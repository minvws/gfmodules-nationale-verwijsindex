from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import MeterProvider, NoOpMeterProvider
from opentelemetry.sdk.metrics import MeterProvider as SdkMeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from app.config import ConfigTelemetry


def create_resource(config: ConfigTelemetry) -> Resource:
    return Resource(attributes={"service.name": config.service_name or "", "service.instance.id": config.instance_id})


def create_meter_provider(config: ConfigTelemetry) -> MeterProvider:
    if not config.metrics_enabled:
        return NoOpMeterProvider()

    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=config.endpoint),
        export_interval_millis=config.metrics_export_interval_ms,
    )
    return SdkMeterProvider(resource=create_resource(config), metric_readers=[reader])
