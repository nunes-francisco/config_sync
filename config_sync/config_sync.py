import click
import subprocess
import sys
import threading
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def setup_logger(log_file):
    """ Configura o log com loguru.
    Args:
        log_file (str): Caminho para o arquivo de log.
    Returns:
        None
    """
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green>  | {level} | <white>{message}</white> | <cyan>(Function: {function}, Line: {line})</cyan>")
    logger.add(log_file, format="{time:YYYY-MM-DD HH:mm:ss:ms} | {level} | {message} | (Function: {function}, Line: {line}) ", level="DEBUG", rotation="10 MB")


def get_nginx_pid():
    """ Retorna o PID do NGINX localmente.
    Returns:
        str: PID do NGINX.
    """
    result = subprocess.run(["/bin/pidof", "nginx"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_logged_in_users():
    """ Retorna os usuários que estão logados localmente."""
    result = subprocess.run(['who'], capture_output=True, text=True)
    if result.returncode == 0:
        users = result.stdout.strip().split('\n')
        logged_users = [user.split()[0] for user in users]
        return list(set(logged_users))  # Remove duplicatas
    else:
        return []


def test_nginx_config():
    """ Testa a configuração do NGINX localmente."""
    logger.trace("Entrou na função test_nginx_config")
    logger.info("Testando configuração do NGINX...")
    result = subprocess.run(["openresty", "-t"], capture_output=True, text=True)
    if result.returncode == 0:
        logger.success("Teste de configuração do NGINX passou.")
        return True
    else:
        logger.error(f"Teste de configuração do NGINX falhou: {result.stderr.strip()}")
        return False


def reload_nginx(nginx_service):
    """ Recarrega o NGINX localmente e registra o PID antigo e novo.
    Args:
        nginx_service (str): Nome do servico do NGINX.
    """
    logger.trace("Entrou na função reload_nginx")
    old_pid = subprocess.getoutput("/bin/pidof nginx")
    logger.info(f"Recarregando {nginx_service} localmente... (PID atual: {old_pid})")
    result = subprocess.run(["sudo", "systemctl", "reload", nginx_service], capture_output=True, text=True)

    if result.returncode == 0:
        new_pid = subprocess.getoutput("/bin/pidof nginx")
        logger.success(f"{nginx_service} recarregado com sucesso. (Novo PID: {new_pid})")
    else:
        logger.error(f"Falha ao recarregar {nginx_service}: {result.stderr.strip()}")


def restart_nginx(nginx_service):
    """ Reinicia o NGINX localmente e registra o PID antigo e novo.
    Args:
        nginx_service (str): Nome do servico do NGINX.
    """
    old_pid = get_nginx_pid()  # Pegar o PID antes do reload
    logger.info(f"Reiniciando {nginx_service} localmente... PID: {old_pid}")
    result = subprocess.run(["sudo", "systemctl", "restart", nginx_service], capture_output=True, text=True)

    if result.returncode == 0:
        new_pid = get_nginx_pid() # Pegar o PID após o reload
        logger.success(f"{nginx_service} reiniciado com sucesso PID: {new_pid}")
    else:
        logger.error(f"Falha ao reiniciar {nginx_service}: {result.stderr.strip()}")


def check_nginx_status():
    """ Verifica o status do NGINX localmente."""
    logger.trace("Entrou na função check_nginx_status")
    result = subprocess.run(["/bin/pidof", "nginx"], capture_output=True, text=True)
    return result.returncode == 0


def sync_remote_config(target_host, watch_folder):
    """ Sincroniza a configuração do NGINX remotamente.
    Args:
        target_host (str): Host alvo.
        watch_folder (str): Caminho da pasta de monitoramento.
    """
    logger.trace("Entrou na função sync_remote_config")
    logger.info(f"Iniciando sincronização remota para {target_host}...", event_type="sync")
    result = subprocess.run(["sudo", "rsync", "-avrz", "-O", "--no-group", "--delete", f"{watch_folder}/", f"francisco.nunes@{target_host}:{watch_folder}"], capture_output=True, text=True)

    if result.returncode == 0:
        logger.success(f"Sincronização remota para {target_host} completada com sucesso.", event_type="sync_success")
    else:
        logger.error(f"Sincronização remota para {target_host} falhou: {result.stderr.strip()}", event_type="sync_failed")


class NginxConfigEventHandler(FileSystemEventHandler):
    """Classe para lidar com eventos de mudança no diretório usando watchdog."""

    def __init__(self, debounce_time, service, reload, restart, remote_sync, target_host, watch_folders):
        self.debounce_time = debounce_time
        self.service = service
        self.reload = reload
        self.restart = restart
        self.remote_sync = remote_sync
        self.target_host = target_host
        self.watch_folders = watch_folders
        self.debounce_timer = None

    def on_modified(self, event):
        #logger.bind(event_type="modified").info(f"File modified: {event.src_path}")
        self.handle_event(event, "modified")

    def on_created(self, event):
       #logger.bind(event_type="created").info(f"File created: {event.src_path}")
        self.handle_event(event, "created")

    def on_deleted(self, event):
        #logger.bind(event_type="deleted").info(f"File deleted: {event.src_path}")
        self.handle_event(event, "deleted")

    def handle_event(self, event, event_type):
        """Reage aos eventos de mudança."""
        logger.trace(f"Evento detectado: {event_type} para o arquivo {event.src_path}")
        # Ignorar arquivos temporários
        if event.src_path.endswith(("swp", "swx", "~", "~lock", ".pid", ".")) or "logs" in event.src_path:
            logger.info(f"Ignorando arquivo temporário ou de log: {event.src_path}")
            return

        # Somente reagir a arquivos .conf
        if not event.src_path.endswith(".conf"):
            logger.info(f"Ignorando arquivo não relacionado à configuração: {event.src_path}")
            return

        user_logged_in = get_logged_in_users()

        if user_logged_in:
            logger.info(f"Detectado login de usuario: {user_logged_in}")
        else:
            logger.info("Nenhum usuario logado.")
            return

        logger.info(f"Arquivo de configuração alterado: {event.src_path} {event_type}.")
        if self.remote_sync:
            logger.info(f"Esperando para sincronizar o NGINX remoto {self.target_host}...")
            self._remote_sync_files()

        if self.restart or self.reload:
            logger.info(" Esperando para reiniciar o NGINX...")
            self._debounce_time(self._reload_or_restart)

    def _debounce_time(self, event):
        """Aguarda o tempo de debounce e reinicia o NGINX, ou sincroniza os arquivos remotamente."""
        # Reiniciar temporizador se outro evento ocorrer antes do tempo limite
        if self.debounce_timer:
            self.debounce_timer.cancel()

        # Configura o temporizador de debounce para evitar múltiplos reinícios
        self.debounce_timer = threading.Timer(self.debounce_time, event)
        self.debounce_timer.start()

    def _reload_or_restart(self):
        """Reinicia o NGINX localmente e registra o PID antigo e novo."""
        if test_nginx_config():
            if self.reload:
                reload_nginx(self.service)
            if self.restart:
                restart_nginx(self.service)
        else:
            logger.error("Teste de configuração do NGINX falhou, reinício cancelado.")

    def _remote_sync_files(self):
        """Sincroniza os arquivos com o servidor remoto configurado."""
        if test_nginx_config():
            if self.remote_sync:
                sync_remote_config(self.target_host, self.watch_folders)

        else:
            logger.error("Teste de configuração do NGINX falhou, sincronização remota cancelada.")

# Função principal usando click para parsear argumentos de linha de comando
@click.command()
@click.option('--debounce-time', default=5.0, help="Tempo de debounce em segundos antes de reiniciar o NGINX.")
@click.option('--reload', is_flag=True, help="Recarrega o NGINX localmente após alterações.")
@click.option('--restart', is_flag=True, help="Reinicia o NGINX localmente após alterações.")
@click.option('--watch-folder', type=str, help="Diretório para monitorar.", default="/usr/local/openresty/nginx")
@click.option('--remote-sync', is_flag=True, help="Sincroniza os arquivos com o servidor remoto configurado.")
@click.option('--remote-restart', is_flag=True, help="Reinicia o NGINX no servidor remoto após sincronização.")
@click.option('--target-host', type=str, help="Especifica o IP ou hostname do servidor remoto.", default="")
@click.option('--service', type=str, help="Nome do serviço NGINX para reiniciar.", default="openresty.service")
@click.option('--log-file', type=str, help="Arquivo de log.", default="/var/log/nginx/config_sync.log")
def main(debounce_time, watch_folder, service, remote_sync, remote_restart, target_host, reload, restart, log_file):
    """Monitora arquivos .conf para reiniciar o NGINX."""
    setup_logger(log_file)

    if (remote_sync or remote_restart) and not target_host:
        logger.error("Para sincronização ou reinício remoto, o parâmetro --target-host é obrigatório.", event_type="error")
        sys.exit(1)

    # Configuração do monitoramento
    event_handler = NginxConfigEventHandler(debounce_time, service, reload, restart, remote_sync, target_host, watch_folder)
    observer = Observer()
    observer.schedule(event_handler, watch_folder, recursive=True)

    logger.info(f"Monitorando o diretório: {watch_folder}")
    observer.start()

    try:
        while observer.is_alive():
            observer.join(1)  # Permite uma pausa de 1 segundo entre verificações
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()