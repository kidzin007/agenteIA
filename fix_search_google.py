with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# O problema está na linha 549 - Erro na estrutura dos blocos try/except
# Vamos substituir o trecho problemático pelo código correto

# Trecho problemático
problematic_code = '''        except requests.exceptions.RequestException as e:
                        logger.warning(f"Erro ao acessar URL {url}: {str(e)}")
                        continue
        except Exception as e:
                        logger.warning(f"Erro ao processar URL {url}: {str(e)}")
                        continue
                
            except Exception as e:
                logger.error(f"Erro durante a pesquisa: {str(e)}")
                return []
            
            logger.info(f"Pesquisa concluída. Encontrados {len(search_results)} resultados.")
            return search_results'''

# Código corrigido
fixed_code = '''        except requests.exceptions.RequestException as e:
                        logger.warning(f"Erro ao acessar URL {url}: {str(e)}")
                        continue
                    except Exception as e:
                        logger.warning(f"Erro ao processar URL {url}: {str(e)}")
                        continue
                
            except Exception as e:
                logger.error(f"Erro durante a pesquisa: {str(e)}")
                return []
            
            logger.info(f"Pesquisa concluída. Encontrados {len(search_results)} resultados.")
            return search_results'''

# Substituindo o código
corrected_content = content.replace(problematic_code, fixed_code)

# Escrevendo o arquivo corrigido
with open('main.py', 'w', encoding='utf-8') as f:
    f.write(corrected_content)

print("Correção aplicada com sucesso!") 