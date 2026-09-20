#Step.1 : Build the OS for docker using FROM langauage : version
FROM python:3.12-slim
#Step.2 : Set the workingdir using WORKDIR /(folder that contains the docker file)
WORKDIR /app
#Step.3 : Copy the requirements of the project using COPY file_name.txt
COPY requirements.txt .
#Step.4 : The excuting once statement using RUN pip install -r file_name.txt
RUN pip install --no-cache-dir  -r requirements.txt
#Step.5 : Copy everything using COPY . .
COPY . . 
#Step.6 : Write the excuting statement for the conatiner that uses CMD [holds the running program commands]
CMD ["uvicorn" , "app.main:app" , "--host" , "0.0.0.0" , "--port" , "8000"]



