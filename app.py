from flask import Flask, render_template, request, redirect, session, send_from_directory, url_for
import mysql.connector 
from mysql.connector import Error
from config import *
from db_functions import *
import os
import time

app = Flask(__name__)
app.secret_key = 'SECRET_KEY'

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    if session:
        if 'adm' in session:
            login = 'adm'
        else:
            login = 'empresa'
    else:
        login = False

    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE vaga.status = 'ativa'
        ORDER BY vaga.id_vaga DESC;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL)
        vagas = cursor.fetchall()
        return render_template('index.html', vagas=vagas, login=login)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

# ROTA DA PÁGINA DE LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session:
        if 'adm' in session:
            return redirect('/adm')
        else:
            return redirect('/empresa')

    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        if not email or not senha:  # Corrigi aqui para verificar ambos os campos corretamente
            erro = "Os campos precisam estar preenchidos!"
            return render_template('login.html', msg_erro=erro)

        if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
            session['adm'] = True
            return redirect('/adm')

        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE email = %s AND senha = %s'
            cursor.execute(comandoSQL, (email, senha))
            empresa = cursor.fetchone()

            if not empresa:
                return render_template('login.html', msgerro='E-mail e/ou senha estão errados!')

            # Acessar os dados como dicionário
            if empresa['status'] == 'inativa':
                return render_template('login.html', msgerro='Empresa desativada! Procure o administrador!')

            session['id_empresa'] = empresa['id_empresa']
            session['nome_empresa'] = empresa['nome_empresa']
            return redirect('/empresa')
        
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

@app.route('/adm')
def adm():
    #Se não houver sessão ativa
    if not session:
        return redirect('/login')
    #Se não for o administrador
    if not 'adm' in session:
        return redirect('/empresa')
  
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM Empresa WHERE status = "ativa"'
        cursor.execute(comandoSQL)
        empresas_ativas = cursor.fetchall()

        comandoSQL = 'SELECT * FROM Empresa WHERE status = "inativa"'
        cursor.execute(comandoSQL)
        empresas_inativas = cursor.fetchall()

        return render_template('adm.html', empresas_ativas=empresas_ativas, empresas_inativas=empresas_inativas)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

    
@app.route('/cadastrar_vaga', methods=['POST','GET'])
def cadastrar_vaga():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')
    
    if request.method == 'GET':
        return render_template('cadastrar_vaga.html')
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = ''
        local = request.form['local']
        salario = ''
        salario = limpar_input(request.form['salario'])
        id_empresa = session['id_empresa']

        if not titulo or not descricao or not formato or not tipo:
            return render_template('cadastrar_vaga.html', msg_erro="Os campos obrigatório precisam estar preenchidos!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            INSERT INTO Vaga (titulo, descricao, formato, tipo, local, salario, id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_empresa))
            conexao.commit()
            return redirect('/empresa')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA PARA CADASTRAR EMPRESAS
@app.route('/cadastrar_empresa', methods=['POST','GET'])
def cadastrarempresa():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se não tem sessão de admin ativa
    if not 'adm' in session:
        return redirect('/login')
    
    if request.method == 'GET':
        return render_template('cadastrarempresa.html')
    
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('cadastrarempresa.html', msg_erro="Os campos obrigatório precisam estar preenchidos!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            INSERT INTO Empresa (nome_empresa, cnpj, telefone, email, senha)
            VALUES (%s, %s, %s, %s, %s)
            '''
            cursor.execute(comandoSQL, (nome_empresa, cnpj, telefone, email, senha))
            conexao.commit()
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062:        
                return render_template('cadastrarempresa.html', msg_erro="O e-mail cadastrado já está em uso!")
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

@app.route('/editar_empresa/<int:id_empresa>', methods=['GET', 'POST'])
def editar_empresa(id_empresa):
    if not session:
        return redirect('/login')
    
    if not session['adm']:
        return redirect('/login')

    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE id_empresa = %s'
            cursor.execute(comandoSQL, (id_empresa,))
            empresa = cursor.fetchone()
            return render_template('editar_empresa.html', empresa=empresa)
        except Error as erro:
            return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor, conexao)

    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('editar_empresa.html', msg_erro ="Todos os campos são obrigatórios!")

        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE empresa
            SET nome_empresa=%s, cnpj=%s, telefone=%s, email=%s, senha=%s
            WHERE id_empresa = %s; 
            '''
            cursor.execute(comandoSQL, (nome_empresa,cnpj,telefone,email,senha,id_empresa))
            conexao.commit()
            return redirect('/adm')
        except Error and erro:
            if erro.errno == 1062:
                return render_template('editar_empresa', msg_erro="Esse email já existe!")
            else:
                return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor,conexao)
    

@app.route('/status_empresa/<int:id_empresa>')
def status(id_empresa):
    if not session:
        return redirect('/login')
    if not session['adm']:
        return redirect('/login')

    try:
        conexao, cursor, = conectar_db()
        comandoSQL = 'SELECT status FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        status_empresa = cursor.fetchone()   

        if status_empresa["status"] == 'ativa':
            novo_status = 'inativa'
        else:
            novo_status = 'ativa'

            

        comandoSQL = '''UPDATE empresa
                        SET status = %s
                        WHERE id_empresa = %s '''

        cursor.execute(comandoSQL, (novo_status, id_empresa))
        conexao.commit()


        if novo_status == 'inativa':

            comandoSQL = '''UPDATE vaga
                            SET status = %s
                            WHERE id_empresa = %s;'''
            cursor.execute(comandoSQL, (novo_status, id_empresa))
        
        conexao.commit()

        return redirect('/adm')

    except Error as erro:
        return f"Erro de BD: {erro}"
    
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    
    finally:
        encerrar_db(cursor, conexao)


@app.route('/excluir_empresa/<int:id_empresa>')
def excluir_empresa(id_empresa):
    if not session:
        return redirect['adm']
    if not session["adm"]:
        return redirect('/login')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'DELETE FROM vaga WHERE id_empresa=%s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()

        comandoSQL = 'DELETE FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        return redirect('/adm')
    except Error as erro:
            return f"Erro de BD: {erro}"
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    finally:
        encerrar_db(cursor, conexao)
    


@app.route('/empresa')
def empresa():
    if not session:
        return redirect('/login')
    if 'adm' in session:
        return redirect('/adm')
    id_empresa = session['id_empresa']
    nome_empresa = session['nome_empresa']

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM vaga WHERE id_empresa = %s AND status = "ativa" ORDER BY id_vaga DESC'
        cursor.execute(comandoSQL, (id_empresa,))
        vagas_ativas = cursor.fetchall()

        comandoSQL = 'SELECT * FROM vaga WHERE id_empresa = %s AND status = "inativa" ORDER BY id_vaga DESC'
        cursor.execute(comandoSQL, (id_empresa,))
        vagas_inativas = cursor.fetchall()

        return render_template('empresa.html', nome_empresa=nome_empresa, vagas_ativas=vagas_ativas, vagas_inativas=vagas_inativas)         
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA EDITAR A VAGA
@app.route('/editar_vaga/<int:id_vaga>', methods=['GET','POST'])
def editarvaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM vaga WHERE id_vaga = %s;'
            cursor.execute(comandoSQL, (id_vaga,))
            vaga = cursor.fetchone()
            return render_template('editar_vaga.html', vaga=vaga)
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = request.form['local']
        salario = limpar_input(request.form['salario'])

        if not titulo or not descricao or not formato or not tipo:
            return redirect('/empresa')
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE vaga SET titulo=%s, descricao=%s, formato=%s, tipo=%s, local=%s, salario=%s
            WHERE id_vaga = %s;
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_vaga))
            conexao.commit()
            return redirect('/empresa')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)


#ROTA PARA ALTERAR O STATUS DA VAGA
@app.route("/status_vaga/<int:id_vaga>")
def status_vaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM vaga WHERE id_vaga = %s;'
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        if vaga['status'] == 'ativa':
            status = 'inativa'
        else:
            status = 'ativa'

        comandoSQL = 'UPDATE vaga SET status = %s WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (status, id_vaga))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA EXCLUIR VAGA
@app.route("/excluir_vaga/<int:id_vaga>")
def excluirvaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'DELETE FROM vaga WHERE id_vaga = %s AND status = "inativa"'
        cursor.execute(comandoSQL, (id_vaga,))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/sobre_vaga/<int:id_vaga>', methods=['GET'])
def sobrevaga(id_vaga):
    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa 
        WHERE vaga.id_vaga = %s;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()

        if not vaga:
            return redirect('/')
        
     
        return render_template('sobrevaga.html', vaga=vaga)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)
  

@app.route('/candidatar/<int:id_vaga>', methods=['GET', 'POST'])
def candidatar(id_vaga):
    if request.method == 'GET':
        try:
            comandoSQL = '''
            SELECT vaga.*, empresa.nome_empresa 
            FROM vaga 
            JOIN empresa ON vaga.id_empresa = empresa.id_empresa 
            WHERE vaga.id_vaga = %s;
            '''
            conexao, cursor = conectar_db()
            cursor.execute(comandoSQL, (id_vaga,))
            vaga = cursor.fetchone()

            if not vaga:
                return redirect('/')
            
            return render_template('candidatar.html',vaga=vaga)

        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

    if request.method == 'POST':

        nome_candidato = request.form['nome']
        email_candidato = request.form['email']
        file = request.files['curriculo']

        if file.filename == '':
            msg = "Nenhum arquivo enviado!"
            return render_template('upload.html', msg=msg)
        
        try:
            timestamp = int(time.time())
            nome_arquivo = f"{timestamp}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            conexao, cursor = conectar_db()
            comandoSQL = "INSERT INTO candidato (id_vaga, nome_candidato, email_candidato, arquivo_curriculo) VALUES (%s, %s, %s, %s)"
            cursor.execute(comandoSQL,(id_vaga, nome_candidato, email_candidato, nome_arquivo,) )
            conexao.commit()
            return redirect(f'/sobre_vaga/{id_vaga}')

        except mysql.connector.Error as erro:
            return render_template('upload.html', msg=f"Erro de BD {erro}")
        except Exception as erro:
            return render_template('upload.html', msg=f"Erro de backend {erro}")
        finally:
            encerrar_db(cursor, conexao)

@app.route('/pesquisar', methods=['GET', 'POST'])
def pesquisar():
    if request.method == 'POST':
        palavras_chave = request.form['palavras_chave']

        if not palavras_chave:
            return redirect('/')

        try:
            comandoSQL = '''
            SELECT vaga.*, empresa.nome_empresa 
            FROM vaga
            JOIN empresa ON vaga.id_empresa = empresa.id_empresa
            WHERE (vaga.titulo LIKE %s OR vaga.descricao LIKE %s)
              AND vaga.status = 'ativa'
            ORDER BY vaga.id_vaga DESC;
            '''
            palavras_chave_formatadas = f"%{palavras_chave}%"
            conexao, cursor = conectar_db()
            cursor.execute(comandoSQL, (palavras_chave_formatadas, palavras_chave_formatadas))
            vagas = cursor.fetchall()
            
            login = 'adm' if 'adm' in session else 'empresa' if 'empresa' in session else False
            return render_template('index.html', vagas=vagas, login=login, palavras_chave=palavras_chave)
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)
    else:
        return redirect('/')
    

@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename,as_attachment=True )

@app.route('/candidatos/<int:id_vaga>')
def candidatos(id_vaga):
    if not session:
        return redirect('/login')
    if 'adm' in session:
        return redirect('/adm')  # Redireciona administradores para a área administrativa

    id_empresa = session['id_empresa']

    try:
        conexao, cursor = conectar_db()
        comandoSQL = """
            SELECT 
               candidato.*, vaga.*
            FROM 
                candidato
            JOIN
             vaga ON candidato.id_vaga = vaga.id_vaga
            WHERE 
                candidato.id_vaga = %s;
        """
        cursor.execute(comandoSQL, (id_vaga,))
        curriculos = cursor.fetchall()

        return render_template('candidatos.html', curriculos=curriculos)

    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/excluir_curriculo/<int:id_vaga>', methods=['POST'])
def excluir_curriculo(id_vaga):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.remove(file_path)

        conexao, cursor = conectar_db()
        comandoSQL = "DELETE FROM candidats WHERE nome_arquivo = %s"
        cursor.execute(comandoSQL, (filename,))
        conexao.commit()

        return redirect('/')
    except mysql.connector.Error as erro:
        return f"Erro de banco de Dados: {erro}"
    except Exception as erro:
        return f"Erro de back-end: {erro}"
    finally:
        encerrar_db(conexao, cursor)

@app.route('/sobre')
def sobre():
    return render_template("sobre.html")

@app.route('/contato')
def contato():
    return render_template("contato.html")

@app.route('/logout')   
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)