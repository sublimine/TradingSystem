file = "src/features/orderbook_l2.py"

with open(file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Cambiar línea 61 de info a debug
lines[60] = lines[60].replace('logger.info("Iceberg detection in DEGRADED MODE")', 
                              'logger.debug("Iceberg detection in DEGRADED MODE")')

with open(file, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Línea 61 corregida: logger.info → logger.debug")
