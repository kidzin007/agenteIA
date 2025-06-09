with open('main.py', 'r', encoding='utf-8') as f:
    content = f.readlines()

# Corrigindo a indentação na linha 1548
problematic_line = 1548 - 1  # Ajustando para indexação 0-based
if 'else:' in content[problematic_line] and len(content[problematic_line].strip()) <= 6:
    # Verificando se a linha seguinte tem indentação incorreta
    if 'await update.message.reply_text' in content[problematic_line + 1]:
        # Corrigindo a indentação
        content[problematic_line + 1] = ' ' * 20 + content[problematic_line + 1].lstrip()
        print(f"Corrigida a indentação na linha {problematic_line + 1}")

# Salvando o arquivo corrigido
with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(content)

print("Correção aplicada com sucesso!") 