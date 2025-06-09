with open('main.py', 'r', encoding='utf-8') as file:
    content = file.readlines()

# Verificando a linha com o erro de indentação
if 'else:\n                await query.message.reply_text(response' in ''.join(content[1886:1888]):
    # Corrigindo a indentação
    print("Linha 1887 antes:", repr(content[1887]))
    content[1887] = '                    ' + content[1887].lstrip()
    print("Linha 1887 depois:", repr(content[1887]))

with open('main.py', 'w', encoding='utf-8') as file:
    file.writelines(content)

print("Correção aplicada.")