file = "src/strategies/iceberg_detection.py"

with open(file, "r", encoding="utf-8") as f:
    content = f.read()

# Cambiar warning a debug para modo degradado
content = content.replace(
    'logger.warning("Iceberg Detection initialized in DEGRADED MODE")',
    'logger.debug("Iceberg Detection initialized in DEGRADED MODE")'
)

content = content.replace(
    'logger.warning("L2 data not available - switching to DEGRADED MODE")',
    'logger.debug("L2 data not available - switching to DEGRADED MODE")'
)

# Cambiar el log repetitivo en cada evaluación
content = content.replace(
    'logger.info("Iceberg detection in DEGRADED MODE")',
    'logger.debug("Iceberg detection in DEGRADED MODE")'
)

with open(file, "w", encoding="utf-8") as f:
    f.write(content)

print("Iceberg logging cambiado de WARNING/INFO a DEBUG")
