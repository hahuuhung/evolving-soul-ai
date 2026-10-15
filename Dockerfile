FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN addgroup --system soul && adduser --system --ingroup soul soul
COPY pyproject.toml README.md LICENSE NOTICE AUTHORS ./
COPY src ./src
RUN python -m pip install --no-cache-dir ".[server,coordinator,demo]"

USER soul
EXPOSE 8765 8770
ENTRYPOINT ["soul"]
CMD ["--help"]

