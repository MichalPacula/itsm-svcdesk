# ai-generated: 70% - Claude Code wrote this script; I ran it against a local Ollama model
"""Stretch 1: one OpenAI-compatible chat call, instrumented with the OpenTelemetry GenAI instrumentation."""

import sys

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.exporter.otlp.json.file import FileSpanExporter
from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

out = sys.argv[1] if len(sys.argv) > 1 else "genai/spans.json"
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(out)))
trace.set_tracer_provider(provider)
OpenAIInstrumentor().instrument()

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
resp = client.chat.completions.create(
    model="qwen3:1.7b",
    messages=[{"role": "user", "content": "In one sentence: what is a known error in ITIL?"}],
    temperature=0.2,
    max_tokens=200,
)
print(resp.choices[0].message.content)
provider.shutdown()
