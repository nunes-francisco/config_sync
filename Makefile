# Makefile para instalação do NGINX Config Sync Service

# Variáveis
PYTHON = python3
PIP = pip install
SERVICE_NAME = nginx_config_sync.service
SCRIPT_NAME = config_sync.py  # Altere para o nome do seu script
WATCH_FOLDER = /usr/local/openresty/nginx
WORKDIRECTORY = /usr/local/bin
NGINX_SERVICE = openresty.service
LOG_FILE = /var/log/nginx/config_sync.log
TARGET_HOST = 10.234.100.13  # Substitua pelo seu IP ou hostname

.PHONY: all install service clean uninstall

all: install service

install:
	@echo "Instalando dependências..."
	$(PIP) -r requirements.txt
	@echo "Instalando o NGINX Config Sync Service..."
	@cp config_sync/config_sync.py $(WORKDIRECTORY)/$(SCRIPT_NAME)

service:
	@echo "Criando o arquivo de unidade systemd..."
	echo "[Unit]" | sudo tee /etc/systemd/system/$(SERVICE_NAME)
	echo "Description=Nginx Config Sync Service" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "After=network.target" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "[Service]" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "Type=simple" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "User=$(USER)" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "WorkingDirectory=$(WORKDIRECTORY)" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "ExecStart=$(PYTHON) $(WORKDIRECTORY)/$(SCRIPT_NAME) --remote-sync --target-host $(TARGET_HOST) --watch-folder $(WATCH_FOLDER) --log-file $(LOG_FILE)" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "Restart=always" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "RestartSec=5" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "[Install]" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)
	echo "WantedBy=multi-user.target" | sudo tee -a /etc/systemd/system/$(SERVICE_NAME)

	@echo "Habilitando e iniciando o serviço..."
	@sudo systemctl daemon-reload
	@sudo systemctl enable $(SERVICE_NAME)
	@sudo systemctl start $(SERVICE_NAME)

clean:
	@echo "Removendo o serviço systemd..."
	@sudo systemctl stop $(SERVICE_NAME)
	@sudo systemctl disable $(SERVICE_NAME)
	@sudo rm -f /etc/systemd/system/$(SERVICE_NAME)
	@echo "Dependências podem ser removidas manualmente."

uninstall:
	@sudo systemctl stop $(SERVICE_NAME)
	@sudo systemctl disable $(SERVICE_NAME)
	@sudo rm -f /etc/systemd/system/$(SERVICE_NAME)
	@echo "Dependências podem ser removidas manualmente."

# Comando padrão a ser executado quando 'make' é chamado sem argumentos
.DEFAULT_GOAL := help

# Ajuda para mostrar as opções disponíveis ao usuário
help:
	@echo "Uso: make [comando]"
	@echo ""
	@echo "Comandos disponíveis:"
	@echo "  all		: Instala e inicia o serviço $(SCRIPT_NAME)"
	@echo "  install	: Instala o serviço $(SCRIPT_NAME)"
	@echo "  clean		: Limpa arquivos temporários ou de saída"
	@echo "  help		: Mostra esta mensagem de ajuda"
	@echo "  service	: Cria o arquivo de unidade systemd"
	@echo "  uninstall	: Desinstala o serviço $(SCRIPT_NAME)"