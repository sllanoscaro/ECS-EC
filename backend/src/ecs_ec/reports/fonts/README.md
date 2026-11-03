# Fuente de reportes

DejaVu Sans 2.37, distribuida con Debian `fonts-dejavu-core`, copiada sin modificaciones.
Origen: https://dejavu-fonts.github.io/ (Bitstream Vera con cambios DejaVu en dominio público).
La licencia y avisos redistribuibles se conservan en [LICENSE.txt](LICENSE.txt).

Archivo: `DejaVuSans.ttf`; SHA-256 `57f73e11f51999432bf7ab22ce55b6f945d5eca1bf824404cfa9ec2e3718c84e`.
El archivo queda versionado y se incluye en el paquete Python y la imagen por el COPY
existente de `backend/`; no requiere paquetes de fuentes del sistema ni red al abrir.
ReportLab debe incrustarlo mediante TTFont. No sustituirlo por una fuente remota.

Verificación de instalación/Unicode/incrustación con lector independiente:
`uv run --locked pytest backend/tests/unit/reports/test_pdf_tooling.py -q`.
Esto valida herramientas, no composición ni generación funcional de005.
