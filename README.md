# NGINX Config Sync Service

Este projeto fornece um script Python para monitorar alterações em configurações do NGINX e sincronizá-las com um servidor remoto, além de recarregar o serviço NGINX quando necessário. O script utiliza `watchdog` para monitorar alterações em um diretório específico e `loguru` para registro de logs.

![Capa](./assets/data-synchronization.png)

## Funcionalidades

- Monitora alterações em arquivos de configuração do NGINX em um diretório específico.
- Testa a configuração do NGINX após cada modificação.
- Recarrega o NGINX localmente quando a configuração é válida.
- Sincroniza os arquivos de configuração com um servidor remoto.
- Possibilidade de reiniciar o NGINX no servidor remoto.
- Registros detalhados de atividades em um arquivo de log.

## Pré-requisitos

Antes de executar o script, você precisa instalar as seguintes dependências:

```shell
pip install click loguru watchdog paramiko
```

Ou carregue o arquivo de requirements.txt

```shell
pip install -r requirements.txt
```

### Uso

O script pode ser executado diretamente na linha de comando. Abaixo estão as opções disponíveis:

```shell
python your_script.py --watch-folder "/caminho/para/nginx" --nginx-service "openresty.service" --remote-sync --remote-restart --target-host "192.168.1.2" --log-file "/var/log/nginx/config_sync.log"
```

### Opções

- ```--reload```: Recarrega o NGINX localmente após alterações.
- `--restart`: Reinicai o serviço do NGINX, após as alterações nas configurações. 
- ```--remote-sync```: Sincroniza os arquivos com o servidor remoto configurado.
- ```--remote-restart```: Reinicia o NGINX no servidor remoto após sincronização.
- ```--target-host```: Especifica o IP ou hostname do servidor remoto.
- ```--watch-folder```: Diretório para monitorar (padrão: /usr/local/openresty/nginx).
- ```--service```: Nome do serviço NGINX para reiniciar (padrão: openresty.service).
- ```--log-file```: Caminho do arquivo de log (padrão: /var/log/nginx/config_sync.log).

### Exemplo  de Execução

```shell
python your_script.py --watch-folder "/usr/local/openresty/nginx" --service "openresty.service" --remote-sync --restart --target-host "192.168.1.2"
```

### Configuração do serviço systemd

Crie um arquivo `.config_sync`  no diretório `/root/.config_sync` , com as váriéveis de ambinete com as configurações necessárias, para execução da aplicação:

```.config_sync```:

```shell
APP=/usr/local/bin/config_sync.py
WATCH_FOLDER=/usr/local/openresty/nginx
LOG_FILE=/var/log/nginx/config_sync.log
PYTHON_PATH=/usr/bin/python3
SERVICE_NAME=openresty.service
TARGET_HOST=10.234.100.13
```



```ini
[Unit]
Description=Nginx Config Sync Service
After=network.target

[Service]
Type=simple
User=root  # Substitua pelo seu usuário
EvironmentFile=/root/.config_sync
WorkingDirectory=/usr/local/bin  # Diretório de trabalho
ExecStart="$PYTHON_PATH" "$APP" --watch-folder "$WATCH_FOLDER" --remote-sync --target-host "$TARGET_HOST" --service "$SERVICE_NAME --log-file "$LOG_FILE"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```



#### Habilitar e iniciar o serviço

Após criar o arquivo de unidade, execute os seguintes comandos:

```bash
# Recarregar os arquivos de unidade
sudo systemctl daemon-reload

# Habilitar o serviço para iniciar automaticamente na inicialização
sudo systemctl enable nginx_config_sync.service

# Iniciar o serviço agora
sudo systemctl start nginx_config_sync.service
```

#### verificando status

```bash
sudo systemctl status nginx_config_sync.service
```

#### **Logs do Serviço**

```bash
sudo journalctl -u nginx_config_sync.service -f
```

#### **Contribuição**

Sinta-se à vontade para contribuir com melhorias ou correções! Crie um fork do repositório, faça suas alterações e envie um pull request.

