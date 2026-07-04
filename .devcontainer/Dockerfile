FROM python:3.14

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    git \
    curl \
    vim \
    build-essential \
    npm

RUN npm install -g @fission-ai/openspec@latest

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["bash"]