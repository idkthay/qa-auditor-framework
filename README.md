# QA Auditor Framework

Framework de auditoria técnica para QA Web desenvolvido em **Python** e **Playwright**, focado na automação de validações técnicas em websites antes da publicação.

O objetivo do projeto é reduzir o tempo gasto em auditorias manuais, padronizar as validações técnicas da equipe de QA e gerar evidências automáticas para apoio à homologação.

---

## ✨ Principais funcionalidades

### Estrutura HTML

- H1 Missing
- H1 Multiple
- H1 Duplicate
- H2 Missing
- Canonical
- Meta Description
- Page Title

---

### URLs

- Client Error (4xx)
- Server Error (5xx)
- Redirects
- URLs com espaços
- URLs com múltiplas barras
- URLs Uppercase
- URLs Non ASCII
- URLs muito longas

---

### Segurança

- HTTPS
- Mixed Content
- HSTS
- X-Frame-Options
- Content Security Policy
- Secure Referrer Policy
- X-Content-Type-Options

---

### Imagens

- Imagens quebradas
- Peso das imagens
- Peso de banners
- ALT ausente
- ALT vazio
- Favicon

---

### Formulários

- Detecção automática
- Método POST
- Botão de envio
- reCAPTCHA
- Máscaras

---

### Responsividade

Capturas automáticas em:

- Desktop
- Tablet
- Mobile

---

### Performance

Integração com:

- Google PageSpeed Insights

---

### Relatórios

Geração automática de:

- JSON técnico
- JSON para importação no Prontuário QA
- Dashboard HTML
- Evidências em screenshots

---

## 📂 Estrutura do projeto

```
qa-auditor-framework/

├── checks/
├── collectors/
├── config/
├── core/
├── crawler/
├── exporters/
├── models/
├── reporters/
├── selectors/
├── services/
├── utils/

├── reports/
├── screenshots/

├── requirements.txt
└── main.py
```

---

## 🚀 Instalação

Clone o projeto:

```bash
git clone https://github.com/idkthay/qa-auditor-framework.git

cd qa-auditor-framework
```

Crie o ambiente virtual:

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Linux/macOS

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Instale os navegadores do Playwright:

```bash
playwright install
```

---

## ⚙️ Configuração

Crie um arquivo `.env` utilizando o `.env.example`.

Exemplo:

```env
PAGESPEED_API_KEY=SUA_CHAVE
```

---

## ▶️ Executando

```bash
python main.py
```

Informe a URL do site quando solicitado.

Exemplo:

```
Digite a URL do site:

https://www.exemplo.com.br
```

---

## 📊 Saídas geradas

Após a execução serão gerados:

```
reports/

auditoria_completa.json

prontuario_automatico.json

relatorio_qa.html
```

e também:

```
screenshots/
```

com todas as evidências coletadas automaticamente.

---

## 🎯 Objetivo da versão 1.0

A versão 1.0 possui foco exclusivo na automação do prontuário técnico utilizado pelo processo de QA da empresa.

Foram priorizadas validações que podem ser corrigidas pela equipe técnica, evitando análises subjetivas de conteúdo ou marketing.

---

## 🛣️ Roadmap

### ✅ Versão 1.0

- Auditoria técnica
- SEO técnico
- Segurança
- Responsividade
- Formulários
- Imagens
- PageSpeed
- Dashboard HTML
- Exportação JSON
- Importação para o Prontuário QA

### 🔮 Futuras versões

Algumas funcionalidades planejadas para versões futuras incluem:

- Interface gráfica (GUI)
- Executável (.exe)
- Histórico de auditorias
- Comparação entre execuções
- Integração com Git
- Dashboard avançado
- Banco de dados

---

## 🛠️ Tecnologias

- Python
- Playwright
- Requests
- BeautifulSoup
- Jinja2
- Google PageSpeed Insights API

---

## 📄 Licença

Projeto desenvolvido para fins internos de automação de auditorias técnicas de QA Web.