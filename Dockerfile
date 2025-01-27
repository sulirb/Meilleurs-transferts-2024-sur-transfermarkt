FROM python:3.9-slim

# Installer les dépendances système pour Firefox et geckodriver
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Installer geckodriver
RUN GECKODRIVER_VERSION=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep -oP '"tag_name": "\K[^"]+') \
    && wget -q -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz \
    && tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ \
    && rm /tmp/geckodriver.tar.gz \
    && chmod +x /usr/local/bin/geckodriver

# Copier l'application
COPY . /app
WORKDIR /app

# Installer les dépendances Python
RUN pip install -r requirements.txt

# Exposer le port
EXPOSE 6789

# Commande pour lancer l'application
CMD ["python", "index.py"]