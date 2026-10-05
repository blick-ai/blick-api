# -*- coding: utf-8 -*-
"""
iac/iac_stack.py — repositorio: blick-api
-------------------------------------------
Define o Model/EndpointConfig/Endpoint do SageMaker via CloudFormation.

Por que via CDK e nao boto3 direto: quem executa a criacao dos recursos
aqui e a EXECUTION ROLE do CloudFormation assumida pelo GitHub Actions
(aluno_22.00667-2_gha_blickapi_v2), nao a identidade SSO pessoal de quem
roda o comando — isso contorna o bloqueio de sagemaker:AddTags que a
conta academica impoe na identidade pessoal dos alunos.

As tags sao aplicadas no nivel do Stack (via Tags.of(), la embaixo no
__init__) e o CloudFormation propaga automaticamente pra todo recurso
dentro dele.
"""

from aws_cdk import CfnOutput, Stack, Tags
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_sagemaker as sagemaker
from constructs import Construct

# tags obrigatorias do ambiente academico — aplicadas aqui dentro do
# Stack (nao via kwarg `tags=` no app.py), porque Tags.of(self).add()
# grava a tag diretamente em cada recurso do template CloudFormation.
# Passar tags=... direto pro construtor do Stack usa outro mecanismo
# (tag de stack do CloudFormation, aplicada so no deploy) que nao
# aparece no template sintetizado — testado e confirmado nesta conversa.
TAGS = {
    "environment": "GRADUACAO",
    "project": "TCC",
    "group": "CMD04",
    "creator": "LUCASCRAPINO_22006672",
    "owner": "BOSSINI",
}

# rede onde o ECS roda (criada manualmente, so referenciada aqui)
VPC_ID = "vpc-00b4be71b7c3587ac"
SUBNETS_ALB = [
    "subnet-057e01dfe46017a5e",  # us-east-1c
    "subnet-0d19adee94a060eea",  # us-east-1b
]
SG_ALB = "sg-0c5dafd2c21aa5664"
PORTA_API = 8000

# conta oficial da AWS que hospeda os containers gerenciados de Deep
# Learning Containers — estavel ha anos, mesma pra maioria das regioes
# comerciais dos EUA (ver tabela oficial se um dia mudarem de regiao)
CONTA_DLC_POR_REGIAO = {
    "us-east-1": "763104351884",
}


def montar_image_uri(region: str, framework_version: str = "2.1.0", py_version: str = "py310") -> str:
    conta_dlc = CONTA_DLC_POR_REGIAO.get(region)
    if not conta_dlc:
        raise ValueError(
            f"Regiao {region!r} nao esta na tabela local de contas DLC — confira "
            f"https://github.com/aws/deep-learning-containers/blob/master/available_images.md"
        )
    return f"{conta_dlc}.dkr.ecr.{region}.amazonaws.com/pytorch-inference:{framework_version}-cpu-{py_version}"


class BlickApiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        model_data_url: str,
        sagemaker_role_arn: str,
        endpoint_name: str = "blick-classificador",
        # 3072MB era suficiente pro modelo unico de deteccao direta; o
        # pipeline novo carrega 2 modelos YOLO ao mesmo tempo (segmentacao
        # + classificacao), por isso o padrao subiu pra 4096MB
        memoria_mb: int = 4096,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = self.region
        image_uri = montar_image_uri(region)

        modelo = sagemaker.CfnModel(
            self, "BlickModel",
            execution_role_arn=sagemaker_role_arn,
            primary_container=sagemaker.CfnModel.ContainerDefinitionProperty(
                image=image_uri,
                model_data_url=model_data_url,
            ),
        )

        endpoint_config = sagemaker.CfnEndpointConfig(
            self, "BlickEndpointConfig",
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name="AllTraffic",
                    model_name=modelo.attr_model_name,
                    # serverless: so cobra pelo tempo de cada chamada, sem
                    # custo parado — ideal pro uso esporadico de teste/TCC
                    serverless_config=sagemaker.CfnEndpointConfig.ServerlessConfigProperty(
                        max_concurrency=5,
                        memory_size_in_mb=memoria_mb,
                    ),
                )
            ],
        )
        endpoint_config.add_resource_dependency(modelo)

        endpoint = sagemaker.CfnEndpoint(
            self, "BlickEndpoint",
            endpoint_config_name=endpoint_config.attr_endpoint_config_name,
            endpoint_name=endpoint_name,
        )
        endpoint.add_resource_dependency(endpoint_config)

        # ---- Application Load Balancer na frente do ECS ----
        # HTTP:80 so; o HTTPS e terminado no API Gateway. Target type "ip"
        # porque a task Fargate usa awsvpc. O ECS service e anexado ao
        # target group depois, via `aws ecs update-service`.
        alb = elbv2.CfnLoadBalancer(
            self, "BlickAlb",
            name="blick-alb",
            type="application",
            scheme="internet-facing",
            subnets=SUBNETS_ALB,
            security_groups=[SG_ALB],
        )

        target_group = elbv2.CfnTargetGroup(
            self, "BlickTargetGroup",
            name="blick-api-tg",
            vpc_id=VPC_ID,
            target_type="ip",
            protocol="HTTP",
            port=PORTA_API,
            health_check_path="/health",
            health_check_protocol="HTTP",
            health_check_interval_seconds=30,
            health_check_timeout_seconds=5,
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
            matcher=elbv2.CfnTargetGroup.MatcherProperty(http_code="200"),
            target_group_attributes=[
                elbv2.CfnTargetGroup.TargetGroupAttributeProperty(
                    key="deregistration_delay.timeout_seconds", value="30"
                )
            ],
        )

        elbv2.CfnListener(
            self, "BlickListener",
            load_balancer_arn=alb.ref,
            port=80,
            protocol="HTTP",
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type="forward", target_group_arn=target_group.ref
                )
            ],
        )

        CfnOutput(self, "AlbDnsName", value=alb.attr_dns_name)
        CfnOutput(self, "TargetGroupArn", value=target_group.ref)

        for chave, valor in TAGS.items():
            Tags.of(self).add(chave, valor)

        self.endpoint_name_output = endpoint_name
