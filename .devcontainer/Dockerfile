FROM python:3.14

ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=1000

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    git \
    curl \
    vim \
    build-essential \
    npm \
    sudo

RUN npm install -g @fission-ai/openspec@latest

# 以與主機相同 uid 的一般使用者開發,避免在 bind mount 的 repo 裡留下 root 擁有的檔案
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && mkdir -p /home/$USERNAME/.claude \
    && chown $USERNAME:$USERNAME /home/$USERNAME/.claude

# 一般使用者無法寫入系統 site-packages,套件裝在使用者擁有的 venv
RUN python -m venv /opt/venv && chown -R $USERNAME:$USERNAME /opt/venv
ENV PATH=/opt/venv/bin:$PATH

USER $USERNAME

CMD ["bash"]
