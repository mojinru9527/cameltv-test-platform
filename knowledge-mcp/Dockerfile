FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY knowledge_mcp_server.py .

ENV SERVER_HOST=0.0.0.0
ENV MCP_PORT=8110

EXPOSE 8110

CMD ["python", "knowledge_mcp_server.py"]
