# base image
FROM python:3.11

# workdir
WORKDIR /video_summerizer

#copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Copy rest of application
COPY . .

#port
EXPOSE 8000

#command
CMD ["streamlit","run","app.py","--host","0.0.0.0","--port","8000"]
