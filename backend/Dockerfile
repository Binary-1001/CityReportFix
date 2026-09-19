#Step.1 : Build the OS for docker using FROM language:version
FROM python:3.12-slim
#Step.2 : Set the working dir inside the container
WORKDIR /app
#Step.3 : Copy the requirements. COPY needs source AND destination
COPY requirements.txt .
#Step.4 : Executed once at build time
RUN pip install --no-cache-dir -r requirements.txt
#Step.5 : Copy everything
COPY . .
#Step.6 : Executed every time the container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]



