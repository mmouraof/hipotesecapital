# Guia de Deploy VPS | Hipótese Capital 🏛️

Este documento descreve o processo passo a passo para realizar o deploy do Terminal Analítico na sua VPS utilizando **Docker**, **Docker Compose** e o domínio **hipotesecapital.duckdns.org**.

---

## 1. Preparação da VPS (Ubuntu/Debian)

Acesse sua VPS via SSH e garanta que o sistema esteja atualizado:

```bash
sudo apt update && sudo apt upgrade -y
```

### Instalar Docker e Docker Compose
Caso ainda não tenha o Docker instalado:

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt install docker-compose -y
```

---

## 2. Configuração do Domínio (DuckDNS)

1. Acesse [duckdns.org](https://www.duckdns.org/).
2. Aponte o domínio `hipotesecapital` para o **IP Público** da sua VPS.
3. Certifique-se de que a porta **8501** (Streamlit) está aberta no firewall da sua VPS (ex: UFW ou painel da nuvem):

```bash
sudo ufw allow 8501/tcp
```

---

## 3. Clonagem e Configuração do Projeto

Na sua VPS, clone o repositório e configure as credenciais:

```bash
# Clone o projeto
git clone https://github.com/seu-usuario/CaseStudyFinance.git
cd CaseStudyFinance

# Crie o arquivo de ambiente
nano .env
```

Dentro do `.env`, insira suas chaves:
```env
OPENAI_API_KEY=sua_chave_openai_aqui
OPENAI_MODEL=gpt-4o-mini
```
*(Pressione `Ctrl+O`, `Enter` e `Ctrl+X` para salvar e sair no nano)*

---

## 4. Deploy com Docker Compose

Construa a imagem e suba o serviço em modo "detatched" (em segundo plano):

```bash
sudo docker-compose up -d --build
```

### Verificação
Para garantir que tudo está rodando:
```bash
sudo docker ps
```
Você deverá ver o container `hipotesse-terminal` ativo na porta `8501`.

---

## 5. Acesso à Aplicação

Agora você pode acessar o terminal através do seu domínio:
`http://hipotesecapital.duckdns.org:8501`

---

## 6. Exposição com Nginx e SSL (Certbot)

Para acessar via `https://hipotesecapital.duckdns.org` (sem a porta 8501 e com segurança), siga estes passos:

### 1. Instalar Nginx e Certbot
```bash
sudo apt install nginx python3-certbot-nginx -y
```

### 2. Abrir Portas de Web Padrão
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw delete allow 8501/tcp  # Opcional: fecha a porta direta para forçar o uso do Nginx
```

### 3. Configurar o Nginx para Streamlit
Crie um arquivo de configuração para o seu domínio:
```bash
sudo nano /etc/nginx/sites-available/hipotesecapital
```

Cole o conteúdo abaixo (ajuste o IP se necessário):
```nginx
server {
    listen 80;
    server_name hipotesecapital.duckdns.org;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Configurações essenciais para WebSockets (Streamlit)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### 4. Ativar a Configuração
```bash
sudo ln -s /etc/nginx/sites-available/hipotesecapital /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Gerar Certificado SSL Gratuito (HTTPS)
```bash
sudo certbot --nginx -d hipotesecapital.duckdns.org
```
- Siga as instruções na tela (coloque seu e-mail e aceite os termos).
- Escolha a opção **2 (Redirect)** para forçar todo o tráfego para HTTPS.

---

## 7. Comandos de Manutenção

- **Ver Logs**: `sudo docker-compose logs -f`
- **Parar Aplicação**: `sudo docker-compose down`
- **Atualizar Código**:
  ```bash
  git pull origin main
  sudo docker-compose up -d --build
  ```
- **Backup do Banco**: O arquivo `database.db` estará na raiz da pasta do projeto na VPS devido ao mapeamento de volume no `docker-compose.yml`.

---
**Suporte Técnico**
Caso o Streamlit exiba erro de "CORS", adicione o seguinte ao comando no `Dockerfile`:
`--server.enableCORS=false --server.enableXsrfProtection=false`
