# CentralFlow — Evolution GO 0.7.2 

Extensão comunitária para canais do WhatsApp. O GitHub Actions compila a aplicação com a extensão e publica sua imagem no GHCR. O EasyPanel baixa a imagem pronta; a VPS não faz o build.

**Estado:** pronto para upload. As imagens ainda não foram publicadas ou testadas no seu GitHub. Aguarde os workflows verdes e teste em um canal próprio antes da produção. Este repositório contém a extensão e a imagem da API, não o painel PHP CentralFlow.

## 1. Fazer o upload

1. Entre como **seifando** e abra https://github.com/new.
2. Crie um repositório **Public** chamado **centralflow-evolution-go**, na branch **main**.
3. Extraia o ZIP no computador. No GitHub, clique em **uploading an existing file** ou **Add file → Upload files**.
4. Envie o **conteúdo da pasta** para a raiz: Dockerfile, README.md, VERSION, scripts, tests, a extensão e os demais arquivos. Não envie só o ZIP, nem uma pasta extra envolvendo tudo.
5. Inclua **`.github/workflows`**. No Windows, ative **Exibir → Mostrar → Itens ocultos**. Se essa pasta não for enviada pelo navegador, use **Add file → Create new file**, digite `.github/workflows/validate.yml`, copie o arquivo local e confirme. Faça o mesmo com `.github/workflows/publish.yml`.
6. Clique em **Commit changes**. Se o navegador limitar a quantidade de arquivos, envie em mais de um lote, mantendo os caminhos. Não acrescente banco, `.env`, chaves ou sessões ao projeto.

## 2. Gerar a imagem no GitHub

1. Abra **Actions** e habilite os workflows, se solicitado.
2. Aguarde **Validate source and Docker image** terminar em verde. Ele verifica os instaladores, compila a aplicação original e testa a inicialização com bancos descartáveis.
3. Abra **Publish validated image to GHCR → Run workflow → main → Run workflow**. A publicação só ocorre depois dos testes e do build.
4. Quando terminar em verde, abra o **Summary** da execução. Copie a referência por **digest** mostrada para o EasyPanel.
5. No perfil GitHub: **Packages → centralflow-evolution-go → Package settings → Change visibility → Public**, se estiver privado. O pacote pode nascer privado mesmo com o repositório público.

Endereço esperado **somente após a primeira publicação bem-sucedida**:

```text
ghcr.io/seifando/centralflow-evolution-go:0.7.2-cf0.6.1
```

Prefira o digest exato do Summary (`ghcr.io/seifando/centralflow-evolution-go@sha256:...`). Não invente esse valor e não tente baixar uma imagem que ainda não foi publicada. Em um fork, o workflow adapta o endereço à conta/repositório de quem o publicou.

O workflow usa runners hospedados no GitHub, permissões limitadas e o `GITHUB_TOKEN` temporário. Não requer token pessoal em arquivo nem acesso à VPS. Quotas e permissões da conta GitHub continuam aplicáveis. A arquitetura inicial é **linux/amd64**; ARM não está incluído.

## 3. Apontar o EasyPanel para o GitHub Container Registry

1. No serviço existente de **Evolution GO 0.7.2**, guarde a imagem anterior e faça backup do banco e dos volumes.
2. Abra **Fonte → Imagem Docker** e cole a referência por digest do Summary do GitHub.
3. Com o pacote público, deixe usuário/senha do registro vazios.
4. Preserve **Ambiente, Domínios, porta interna, comando e Volumes** da instalação original que já funciona.
5. Clique em **Salvar → Implantar** uma vez. Confira **Implantações** e **Logs** antes de continuar.
6. Não execute dois serviços usando a mesma sessão/volume de WhatsApp. Nessa instalação, mantenha uma réplica.

**Não use Fonte GitHub, Git ou Dockerfile no EasyPanel:** isso faria o build voltar para a VPS. A referência GHCR é a ligação entre GitHub e EasyPanel.

Para instalação nova, configure primeiro a versão original 0.7.2 e as dependências conforme a documentação oficial; depois troque a imagem. O projeto não cria credenciais de produção nem migra sessões/bancos entre API e GO. As credenciais dos testes são descartáveis e não devem ser usadas na hospedagem.

## 4. Configuração no CentralFlow

1. Use o painel PHP CentralFlow **0.6.0 ou superior**. Em **Atualização e guia → Atualizar banco de dados**, aplique as migrações.
2. Em **WhatsApp**, selecione **Evolution GO**, informe a **URL HTTPS pública** da API e a **chave global** atual. O hostname deve constar dos hosts autorizados na configuração privada do CentralFlow. Clique em **Validar e salvar**.
3. Clique em **Sincronizar instâncias**, escolha a instância existente e confira se ela está conectada. Defina a principal, se necessário.
4. **Ativar recebimento** aponta o webhook da instância para o CentralFlow e substitui o webhook atual; use quando quiser essa integração.
5. Em **Canais e Status → Configuração**, escolha a instância e clique em **Consultar suporte**. Deve retornar `centralflow-publishing/1` e a operação `sync`.
6. Abra **Canais → Sincronizar canais existentes**. A consulta cadastra/atualiza os canais vinculados retornados pelo WhatsApp; não segue canais novos nem apaga os ausentes na resposta.
7. Teste primeiro em um canal próprio: importar, consultar e publicar. Editar/publicar exige administrador ou proprietário; excluir exige proprietário.
8. Para agendar com o painel fechado, mantenha **cron.php a cada minuto na hospedagem PHP**. Os workflows não configuram esse agendador.

## Escopo e limites

- Criar/importar, consultar, sincronizar, seguir/deixar, editar/excluir com permissão, publicar texto/imagem/vídeo e ler publicações disponibilizadas pelo provedor.
- As versões, commits e hashes estão fixados em `upstream.json`. Outra versão exige revisão: não troque apenas a tag nem desative os hashes.
- Testes locais conferem o instalador e partes do contrato. O CI deve conferir o build completo em Linux e a inicialização. Nenhum teste conecta um WhatsApp real ou envia mensagens. Uma execução verde não comprova todos os fluxos da conta.
- O WhatsApp pode limitar a resposta. Visualizações/curtidas anônimas não identificam consumidores; as regras de consentimento do CentralFlow continuam válidas.
- A economia principal é retirar o build da VPS. Cerca de 1 GB de RAM pode continuar insuficiente para painel, APIs e bancos. Dimensione pelo uso real; não imponha limites de memória arbitrariamente baixos.
- Preserve as licenças, marcas, autenticação e avisos originais. Este projeto comunitário não é uma distribuição oficial da Evolution Foundation.

## Reverter

Retorne à imagem anterior no mesmo serviço, preservando banco, ambiente e volumes. A extensão acrescenta rotas e arquivos. A troca pode executar o bootstrap/migrações nativos da versão original: mantenha os backups.

## Contribuir e relatar problemas

Abra issues e pull requests sem credenciais, QR, sessões ou dados de clientes. Informe provedor, versão, arquitetura e digest da imagem. Preserve as verificações de segurança, permissões e licenciamento. Consulte `LICENSE`, `NOTICE`, `LICENSES` e `docs/COMPATIBILIDADE.md`.

Referências oficiais: https://github.com/evolution-foundation/evolution-go ; https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images ; https://easypanel.io/docs/services/app .
