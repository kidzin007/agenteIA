with open('main.py', 'r', encoding='utf-8') as f:
    content = f.readlines()

# Procurando o bloco problemático
start_line = 0
for i, line in enumerate(content):
    if "welcome_message = (" in line and "greeting" in content[i+1]:
        start_line = i
        break

if start_line > 0:
    # Encontramos o problema, vamos corrigir
    corrected_lines = []
    
    # Adicionando a primeira definição de welcome_message corretamente
    corrected_lines.append('                    welcome_message = (\n')
    corrected_lines.append('                        f"{greeting}\\n\\n"\n')
    corrected_lines.append('                        f"Da última vez conversamos sobre {topics_text}. Como posso te ajudar hoje? "\n')
    corrected_lines.append('                        f"Escolha uma das opções abaixo ou me faça uma pergunta direta."\n')
    corrected_lines.append('                    )\n')
    
    # Substituindo o conteúdo no arquivo original
    content[start_line:start_line+5] = corrected_lines
    
    # Escrevendo de volta ao arquivo
    with open('main.py', 'w', encoding='utf-8') as f:
        f.writelines(content)
    
    print("Correção aplicada com sucesso!")
else:
    print("Não foi possível encontrar o bloco problemático.") 