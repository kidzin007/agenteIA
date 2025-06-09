def fix_indentation(file_path='main.py'):
    """Corrige problemas de indentação no código Python"""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    fixed = False
    # Verificando padrões problemáticos de indentação
    for i in range(1, len(lines) - 1):
        # Verificando blocos else: seguidos por linhas com indentação incorreta
        if lines[i].strip() == 'else:' and lines[i+1].strip().startswith('await') and not lines[i+1].startswith('                    '):
            lines[i+1] = '                    ' + lines[i+1].lstrip()
            print(f"Corrigido erro de indentação na linha {i+1}")
            fixed = True
    
    if fixed:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)
        print("Correções aplicadas com sucesso!")
    else:
        print("Nenhum erro de indentação encontrado!")

if __name__ == "__main__":
    fix_indentation() 