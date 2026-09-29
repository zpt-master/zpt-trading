# ZptMaster Intel x402 service — self-contained, stdlib-only.
FROM python:3.12-slim
WORKDIR /app
COPY intel_server.py payverify.py ./
COPY fxintel ./fxintel
ENV PORT=8080
EXPOSE 8080
# intel_server binds 0.0.0.0:$PORT in production; reads PORT env.
CMD ["python3","-u","intel_server.py","--host","0.0.0.0","--port","8080"]
