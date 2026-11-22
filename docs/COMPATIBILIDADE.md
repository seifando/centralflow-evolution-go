# Compatibilidade

Use os commits e versões fixados em upstream.json. Não há promessa de compatibilidade universal com outros forks/versões. O CentralFlow PHP deve ser 0.6.0 ou superior, com banco atualizado. O CI não conecta uma conta real ao WhatsApp.

**Evolution GO 0.7.2**: preserva o licenciamento e a ativação originais, sem removê-los ou contorná-los. Conclua a ativação nativa quando exigida pelo fornecedor. O smoke test reconhece a barreira nativa de licença como servidor HTTP iniciado, não como licença ativada ou canais funcionais.

A chave global autentica as rotas administrativas. Operações WhatsApp usam token próprio da instância, recebido e armazenado criptografado pelo CentralFlow ao sincronizar. A consulta de canais é nativa; edição, exclusão e publicação usam as rotas adicionais. O Status segue a privacidade da conta: seleção de números por postagem não é suportada nesse contrato.
