with open('main.py', 'r', encoding='utf-8') as f:
    content = f.readlines()

# O problema está na estrutura if/else na função start, por volta das linhas 1540-1550
# Vamos reconstruir esse trecho corretamente

# Detectando o início do bloco problemático
start_line = 0
end_line = 0
for i, line in enumerate(content):
    if "topics = user_info" in line and "[:2]" in line:
        start_line = i - 5  # Pegando algumas linhas antes para contexto
    if "# Novo usuário - mensagem padrão" in line:
        end_line = i + 10  # Pegando algumas linhas depois para contexto
        break

if start_line > 0 and end_line > start_line:
    print(f"Encontrado bloco problemático de {start_line+1} a {end_line+1}")
    
    # Corrigindo a indentação
    corrected_block = []
    
    # Adicionando as linhas anteriores ao bloco if
    for i in range(start_line, start_line + 10):
        corrected_block.append(content[i])
    
    # Adicionando o bloco welcome_message corretamente indentado
    corrected_block.append("                welcome_message = (\n")
    corrected_block.append("                    f\"{greeting}\\n\\n\"\n")
    corrected_block.append("                    f\"Da última vez conversamos sobre {topics_text}. Como posso te ajudar hoje? \"\n")
    corrected_block.append("                    f\"Escolha uma das opções abaixo ou me faça uma pergunta direta.\"\n")
    corrected_block.append("                )\n")
    
    # Adicionando o else corretamente indentado
    corrected_block.append("                else:\n")
    corrected_block.append("                    welcome_message = (\n")
    corrected_block.append("                        f\"{greeting}\\n\\n\"\n")
    corrected_block.append("                        f\"Como posso te ajudar hoje? Escolha uma das opções abaixo ou me faça uma pergunta direta.\"\n")
    corrected_block.append("                    )\n")
    
    # Adicionando o else principal corretamente indentado
    corrected_block.append("            else:\n")
    corrected_block.append("                # Novo usuário - mensagem padrão\n")
    corrected_block.append("                welcome_message = (\n")
    corrected_block.append("                    f\"Olá, {user.first_name}! 👋\\n\\n\"\n")
    corrected_block.append("                    \"Sou Paulo, consultor financeiro com mais de 15 anos de experiência no mercado. \"\n")
    corrected_block.append("                    \"Estou aqui para ajudar com suas dúvidas sobre investimentos, planejamento financeiro e economia.\\n\\n\"\n")
    corrected_block.append("                    \"Como posso auxiliar você hoje? Escolha uma opção abaixo ou me faça uma pergunta direta sobre qualquer tema financeiro.\"\n")
    corrected_block.append("                )\n")
    
    # Substituindo o bloco problemático pelo corrigido
    content[start_line:end_line+1] = corrected_block
    
    # Salvando o arquivo corrigido
    with open('main.py', 'w', encoding='utf-8') as f:
        f.writelines(content)
    
    print("Correção aplicada com sucesso!")
else:
    print("Não foi possível identificar o bloco problemático. Verificando outras abordagens...")
    
    # Tentando outra abordagem - corrigindo diretamente a linha 1547-1548
    try:
        line_1547 = 1547 - 1  # Ajustando para índice 0-based
        line_1548 = 1548 - 1
        
        if "else:" in content[line_1547]:
            # Verificando e corrigindo a indentação
            content[line_1547] = "            else:\n"
            print(f"Corrigida indentação da linha 1547: {content[line_1547].strip()}")
            
        # Salvando o arquivo corrigido
        with open('main.py', 'w', encoding='utf-8') as f:
            f.writelines(content)
        
        print("Correção alternativa aplicada com sucesso!")
    except Exception as e:
        print(f"Erro ao aplicar correção alternativa: {str(e)}") 