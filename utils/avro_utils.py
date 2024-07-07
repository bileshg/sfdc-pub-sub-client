import io
import logging
import avro.io
import avro.schema

logger = logging.getLogger(__name__)


def encode(schema, payload):
    schema = avro.schema.parse(schema)
    buf = io.BytesIO()
    encoder = avro.io.BinaryEncoder(buf)
    writer = avro.io.DatumWriter(schema)
    writer.write(payload, encoder)
    return buf.getvalue()


def decode(schema, payload):
    avro_schema = avro.schema.parse(schema)
    buf = io.BytesIO(payload)
    decoder = avro.io.BinaryDecoder(buf)
    reader = avro.io.DatumReader(avro_schema)
    return reader.read(decoder)
