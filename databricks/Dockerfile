FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY app.py mcp_server.py ui.py evolved_tools.json ./
COPY static/ ./static/
COPY templates/ ./templates/

# Azure Web App injects PORT at runtime (default 8080)
ENV PORT=8080

EXPOSE 8080

CMD ["python", "app.py", "--ui"]
