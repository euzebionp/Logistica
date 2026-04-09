import sqlite3
import pandas as pd
import os

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(SCRIPT_DIR, "traffic_app.db")

def get_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    """Initializes the database with the required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table: motoristas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS motoristas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            cnh TEXT NOT NULL UNIQUE,
            validade_cnh TEXT NOT NULL
        )
    ''')
    
    # Table: veiculos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL UNIQUE,
            modelo TEXT NOT NULL,
            ano INTEGER NOT NULL,
            renavam TEXT NOT NULL UNIQUE,
            km_atual REAL DEFAULT 0
        )
    ''')
    
    # Table: multas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS multas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            hora_infracao TEXT,
            local TEXT NOT NULL,
            tipo_infracao TEXT NOT NULL,
            descricao TEXT,
            motorista_id INTEGER NOT NULL,
            veiculo_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            viagem_id INTEGER,
            FOREIGN KEY (motorista_id) REFERENCES motoristas (id),
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id),
            FOREIGN KEY (viagem_id) REFERENCES viagens (id)
        )
    ''')
    
    # Table: viagens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS viagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            motorista_id INTEGER NOT NULL,
            veiculo_id INTEGER NOT NULL,
            origem TEXT NOT NULL DEFAULT '',
            destino TEXT NOT NULL,
            hora_saida TEXT NOT NULL,
            distancia REAL DEFAULT 0,
            FOREIGN KEY (motorista_id) REFERENCES motoristas (id),
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
        )
    ''')
    
    # Table: manutencoes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manutencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            tipo_servico TEXT NOT NULL,
            descricao TEXT,
            km_realizado REAL NOT NULL,
            proximo_servico_km REAL,
            proximo_servico_data TEXT,
            valor REAL NOT NULL,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
        )
    ''')

    # Table: abastecimentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS abastecimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER,
            identificacao TEXT NOT NULL,
            numero_frota TEXT,
            data TEXT NOT NULL,
            tipo_combustivel TEXT NOT NULL,
            volume_litros REAL NOT NULL,
            preco_litro REAL NOT NULL,
            valor_total REAL NOT NULL,
            km_anterior REAL DEFAULT 0,
            km_atual REAL NOT NULL,
            km_rodados REAL,
            rendimento_kml REAL,
            lote_importacao TEXT,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
        )
    ''')

    # Table: planos_manutencao
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS planos_manutencao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL,
            tipo_servico TEXT NOT NULL,
            intervalo_km REAL,
            ultima_km REAL,
            proxima_km REAL,
            intervalo_horas REAL,
            ultima_horas REAL,
            proxima_horas REAL,
            intervalo_dias INTEGER,
            ultima_data TEXT,
            proxima_data TEXT,
            prioridade TEXT DEFAULT 'normal',
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
        )
    ''')

    # ============ MIGRATIONS ============
    migrations = [
        "ALTER TABLE veiculos ADD COLUMN km_atual REAL DEFAULT 0",
        "ALTER TABLE veiculos ADD COLUMN tipo_combustivel TEXT DEFAULT 'flex'",
        "ALTER TABLE veiculos ADD COLUMN numero_frota TEXT",
        "ALTER TABLE veiculos ADD COLUMN hodometro_horas REAL DEFAULT 0",
        "ALTER TABLE viagens ADD COLUMN distancia REAL DEFAULT 0",
        "ALTER TABLE viagens ADD COLUMN origem TEXT DEFAULT ''",
        "ALTER TABLE viagens ADD COLUMN km_atual REAL",
        "ALTER TABLE multas ADD COLUMN hora_infracao TEXT",
        "ALTER TABLE multas ADD COLUMN viagem_id INTEGER REFERENCES viagens(id)",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

def check_driver_exists(cpf):
    """Checks if a driver with the given CPF already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM motoristas WHERE cpf = ?", (cpf,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def check_vehicle_exists(placa):
    """Checks if a vehicle with the given license plate already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM veiculos WHERE placa = ?", (placa,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def check_renavam_exists(renavam):
    """Checks if a vehicle with the given Renavam already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM veiculos WHERE renavam = ?", (renavam,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def add_driver(nome, cpf, cnh, validade_cnh):
    """Adds a new driver to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO motoristas (nome, cpf, cnh, validade_cnh)
            VALUES (?, ?, ?, ?)
        ''', (nome, cpf, cnh, validade_cnh))
        conn.commit()
        return True, "Motorista cadastrado com sucesso!"
    except sqlite3.IntegrityError as e:
        return False, f"Erro ao cadastrar motorista: {e}"
    finally:
        conn.close()

def add_vehicle(placa, modelo, ano, renavam, km_atual=0,
                tipo_combustivel='flex', numero_frota=None, hodometro_horas=0):
    """Adds a new vehicle to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO veiculos (placa, modelo, ano, renavam, km_atual,
                                  tipo_combustivel, numero_frota, hodometro_horas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (placa, modelo, ano, renavam, km_atual,
              tipo_combustivel, numero_frota, hodometro_horas))
        conn.commit()
        return True, "Veículo cadastrado com sucesso!"
    except sqlite3.IntegrityError as e:
        return False, f"Erro ao cadastrar veículo: {e}"
    finally:
        conn.close()

def add_fine(data, local, tipo_infracao, descricao, motorista_id, veiculo_id, valor, hora_infracao=None, viagem_id=None):
    """Adds a new fine to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO multas (data, hora_infracao, local, tipo_infracao, descricao, motorista_id, veiculo_id, valor, viagem_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data, hora_infracao, local, tipo_infracao, descricao, motorista_id, veiculo_id, valor, viagem_id))
        conn.commit()
        return True, "Multa cadastrada com sucesso!"
    except Exception as e:
        return False, f"Erro ao cadastrar multa: {e}"
    finally:
        conn.close()

def get_drivers():
    """Returns a DataFrame with all drivers."""
    conn = get_connection()
    query = "SELECT * FROM motoristas"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_vehicles():
    """Returns a DataFrame with all vehicles."""
    conn = get_connection()
    query = "SELECT * FROM veiculos"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_fines_df():
    """Returns a DataFrame with details of all fines."""
    conn = get_connection()
    query = '''
        SELECT 
            m.id, 
            m.data, 
            m.local, 
            m.tipo_infracao, 
            m.descricao, 
            m.valor,
            mot.nome as motorista, 
            v.placa as veiculo_placa,
            v.modelo as veiculo_modelo
        FROM multas m
        JOIN motoristas mot ON m.motorista_id = mot.id
        JOIN veiculos v ON m.veiculo_id = v.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ============ UPDATE FUNCTIONS ============

def update_driver(driver_id, nome, cpf, cnh, validade_cnh):
    """Updates an existing driver's information."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE motoristas 
            SET nome = ?, cpf = ?, cnh = ?, validade_cnh = ?
            WHERE id = ?
        ''', (nome, cpf, cnh, validade_cnh, driver_id))
        conn.commit()
        return True, "Motorista atualizado com sucesso!"
    except sqlite3.IntegrityError as e:
        return False, f"Erro ao atualizar motorista: {e}"
    finally:
        conn.close()

def update_vehicle(vehicle_id, placa, modelo, ano, renavam, km_atual,
                   tipo_combustivel=None, numero_frota=None, hodometro_horas=None):
    """Updates an existing vehicle's information."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if tipo_combustivel is not None:
            cursor.execute('''
                UPDATE veiculos 
                SET placa = ?, modelo = ?, ano = ?, renavam = ?, km_atual = ?,
                    tipo_combustivel = ?, numero_frota = ?, hodometro_horas = ?
                WHERE id = ?
            ''', (placa, modelo, ano, renavam, km_atual,
                  tipo_combustivel, numero_frota, hodometro_horas, vehicle_id))
        else:
            cursor.execute('''
                UPDATE veiculos 
                SET placa = ?, modelo = ?, ano = ?, renavam = ?, km_atual = ?
                WHERE id = ?
            ''', (placa, modelo, ano, renavam, km_atual, vehicle_id))
        conn.commit()
        return True, "Veículo atualizado com sucesso!"
    except sqlite3.IntegrityError as e:
        return False, f"Erro ao atualizar veículo: {e}"
    finally:
        conn.close()

def update_fine(fine_id, data, local, tipo_infracao, descricao, motorista_id, veiculo_id, valor):
    """Updates an existing fine's information."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE multas 
            SET data = ?, local = ?, tipo_infracao = ?, descricao = ?, 
                motorista_id = ?, veiculo_id = ?, valor = ?
            WHERE id = ?
        ''', (data, local, tipo_infracao, descricao, motorista_id, veiculo_id, valor, fine_id))
        conn.commit()
        return True, "Multa atualizada com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar multa: {e}"
    finally:
        conn.close()

# ============ DELETE FUNCTIONS ============

def delete_driver(driver_id):
    """Deletes a driver from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if driver has associated fines
        cursor.execute("SELECT COUNT(*) FROM multas WHERE motorista_id = ?", (driver_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            return False, f"Não é possível excluir. Este motorista possui {count} multa(s) associada(s)."
        
        cursor.execute("DELETE FROM motoristas WHERE id = ?", (driver_id,))
        conn.commit()
        return True, "Motorista excluído com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir motorista: {e}"
    finally:
        conn.close()

def delete_vehicle(vehicle_id):
    """Deletes a vehicle from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if vehicle has associated fines
        cursor.execute("SELECT COUNT(*) FROM multas WHERE veiculo_id = ?", (vehicle_id,))
        count_fines = cursor.fetchone()[0]
        if count_fines > 0:
            return False, f"Não é possível excluir. Este veículo possui {count_fines} multa(s) associada(s)."
        
        # Check if vehicle has associated travels
        cursor.execute("SELECT COUNT(*) FROM viagens WHERE veiculo_id = ?", (vehicle_id,))
        count_travels = cursor.fetchone()[0]
        if count_travels > 0:
            return False, f"Não é possível excluir. Este veículo possui {count_travels} viagem(ns) associada(s)."

        # Check if vehicle has associated maintenances
        cursor.execute("SELECT COUNT(*) FROM manutencoes WHERE veiculo_id = ?", (vehicle_id,))
        count_maintenances = cursor.fetchone()[0]
        if count_maintenances > 0:
            return False, f"Não é possível excluir. Este veículo possui {count_maintenances} manutenção(ões) associada(s)."
        
        cursor.execute("DELETE FROM veiculos WHERE id = ?", (vehicle_id,))
        conn.commit()
        return True, "Veículo excluído com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir veículo: {e}"
    finally:
        conn.close()

def delete_fine(fine_id):
    """Deletes a fine from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM multas WHERE id = ?", (fine_id,))
        conn.commit()
        return True, "Multa excluída com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir multa: {e}"
    finally:
        conn.close()

# ============ GETTER FUNCTIONS FOR SINGLE RECORDS ============

def get_driver_by_id(driver_id):
    """Returns a single driver by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM motoristas WHERE id = ?", (driver_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'id': result[0],
            'nome': result[1],
            'cpf': result[2],
            'cnh': result[3],
            'validade_cnh': result[4]
        }
    return None

def get_vehicle_by_id(vehicle_id):
    """Returns a single vehicle by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, placa, modelo, ano, renavam, km_atual, "
                   "tipo_combustivel, numero_frota, hodometro_horas "
                   "FROM veiculos WHERE id = ?", (vehicle_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'id': result[0],
            'placa': result[1],
            'modelo': result[2],
            'ano': result[3],
            'renavam': result[4],
            'km_atual': result[5] if result[5] is not None else 0,
            'tipo_combustivel': result[6] if result[6] else 'flex',
            'numero_frota': result[7] if result[7] else '',
            'hodometro_horas': result[8] if result[8] is not None else 0,
        }
    return None

def get_vehicle_by_placa_or_frota(identificacao, numero_frota=None):
    """Find vehicle by plate (identificacao) or fleet number."""
    conn = get_connection()
    cursor = conn.cursor()
    identificacao_upper = str(identificacao).strip().upper()
    cursor.execute(
        "SELECT id FROM veiculos WHERE UPPER(placa) = ?",
        (identificacao_upper,)
    )
    result = cursor.fetchone()
    if not result and numero_frota:
        cursor.execute(
            "SELECT id FROM veiculos WHERE numero_frota = ?",
            (str(numero_frota).strip(),)
        )
        result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_fine_by_id(fine_id):
    """Returns a single fine by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM multas WHERE id = ?", (fine_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'id': result[0],
            'data': result[1],
            'local': result[2],
            'tipo_infracao': result[3],
            'descricao': result[4],
            'motorista_id': result[5],
            'veiculo_id': result[6],
            'valor': result[7]
        }
    return None

# ============ TRAVEL FUNCTIONS ============

def add_travel(data, motorista_id, veiculo_id, origem, destino, hora_saida, distancia=0, km_atual=None):
    """Adds a new travel to the database and updates vehicle mileage."""
    conn = get_connection()
    cursor = conn.cursor()
    alert_message = None
    
    try:
        cursor.execute('''
            INSERT INTO viagens (data, motorista_id, veiculo_id, origem, destino, hora_saida, distancia, km_atual)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data, motorista_id, veiculo_id, origem, destino, hora_saida, distancia, km_atual))
        
        # Update vehicle mileage
        final_km = 0
        if km_atual:
            final_km = km_atual
            cursor.execute('''
                UPDATE veiculos 
                SET km_atual = ?
                WHERE id = ?
            ''', (km_atual, veiculo_id))
        elif distancia > 0:
            # Get current km to calculate final
            cursor.execute("SELECT km_atual FROM veiculos WHERE id = ?", (veiculo_id,))
            curr = cursor.fetchone()
            current_val = curr[0] if curr and curr[0] else 0
            final_km = current_val + distancia
            
            cursor.execute('''
                UPDATE veiculos 
                SET km_atual = km_atual + ?
                WHERE id = ?
            ''', (distancia, veiculo_id))
            
        conn.commit()
        
        # Check for maintenance
        if final_km > 0:
            is_due, msg = check_maintenance_due(veiculo_id, final_km)
            if is_due:
                alert_message = msg
                
        success_msg = "Viagem cadastrada com sucesso!"
        if alert_message:
            success_msg += f" {alert_message}"
            
        return True, success_msg
    except Exception as e:
        return False, f"Erro ao cadastrar viagem: {e}"
    finally:
        conn.close()

def get_travels():
    """Returns a DataFrame with all travels."""
    conn = get_connection()
    query = '''
        SELECT 
            v.id,
            v.data,
            v.hora_saida,
            v.origem,
            v.destino,
            v.distancia,
            v.km_atual,
            m.nome as motorista,
            ve.placa as veiculo_placa,
            ve.modelo as veiculo_modelo
        FROM viagens v
        JOIN motoristas m ON v.motorista_id = m.id
        JOIN veiculos ve ON v.veiculo_id = ve.id
        ORDER BY v.data DESC, v.hora_saida DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_travel_by_id(travel_id):
    """Returns a single travel by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM viagens WHERE id = ?", (travel_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'id': result[0],
            'data': result[1],
            'motorista_id': result[2],
            'veiculo_id': result[3],
            'origem': result[4] if len(result) > 7 else '', # Handle migration
            'destino': result[5] if len(result) > 7 else result[4], # Shift if old schema
            'hora_saida': result[6] if len(result) > 7 else result[5],
            'distancia': result[7] if len(result) > 7 else (result[6] if len(result) > 6 else 0),
            'km_atual': result[8] if len(result) > 8 else 0
        }
    return None

def update_travel(travel_id, data, motorista_id, veiculo_id, origem, destino, hora_saida, distancia, km_atual=None):
    """Updates an existing travel's information and adjusts vehicle mileage."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Update the travel record
        cursor.execute('''
            UPDATE viagens 
            SET data = ?, motorista_id = ?, veiculo_id = ?, origem = ?, destino = ?, hora_saida = ?, distancia = ?, km_atual = ?
            WHERE id = ?
        ''', (data, motorista_id, veiculo_id, origem, destino, hora_saida, distancia, km_atual, travel_id))
        
        # Update vehicle mileage if km_atual is provided
        if km_atual and km_atual > 0:
            cursor.execute('''
                UPDATE veiculos 
                SET km_atual = ?
                WHERE id = ?
            ''', (km_atual, veiculo_id))
        
        conn.commit()
        return True, "Viagem atualizada com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar viagem: {e}"
    finally:
        conn.close()

def delete_travel(travel_id):
    """Deletes a travel from the database and reverts mileage."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check if travel has associated fines
        cursor.execute("SELECT COUNT(*) FROM multas WHERE viagem_id = ?", (travel_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            return False, f"Não é possível excluir. Esta viagem possui {count} multa(s) associada(s)."
        
        # Get distance to revert mileage
        cursor.execute("SELECT veiculo_id, distancia FROM viagens WHERE id = ?", (travel_id,))
        travel = cursor.fetchone()
        
        if travel:
            veiculo_id = travel[0]
            distancia = travel[1] if travel[1] else 0
            
            # Revert mileage
            cursor.execute('''
                UPDATE veiculos 
                SET km_atual = km_atual - ?
                WHERE id = ?
            ''', (distancia, veiculo_id))
        
        cursor.execute("DELETE FROM viagens WHERE id = ?", (travel_id,))
        conn.commit()
        return True, "Viagem excluída com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir viagem: {e}"
    finally:
        conn.close()

# ============ MAINTENANCE FUNCTIONS ============

def check_maintenance_due(vehicle_id, current_km):
    """Checks if maintenance is due for the vehicle."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get max next service km
    cursor.execute('''
        SELECT MAX(proximo_servico_km) 
        FROM manutencoes 
        WHERE veiculo_id = ?
    ''', (vehicle_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        next_service = result[0]
        if current_km >= next_service:
            return True, f"⚠️ MANUTENÇÃO VENCIDA! O veículo atingiu {current_km} km. Próxima revisão era aos {next_service} km."
        elif (next_service - current_km) <= 1000:
            return True, f"⚠️ Manutenção Próxima! Faltam {next_service - current_km:.0f} km para a revisão."
            
    return False, None

def add_maintenance(veiculo_id, data, tipo_servico, descricao, km_realizado, proximo_servico_km, proximo_servico_data, valor):
    """Adds a new maintenance record."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO manutencoes (veiculo_id, data, tipo_servico, descricao, km_realizado, proximo_servico_km, proximo_servico_data, valor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (veiculo_id, data, tipo_servico, descricao, km_realizado, proximo_servico_km, proximo_servico_data, valor))
        conn.commit()
        return True, "Manutenção registrada com sucesso!"
    except Exception as e:
        return False, f"Erro ao registrar manutenção: {e}"
    finally:
        conn.close()

def get_maintenances():
    """Returns a DataFrame with all maintenance records."""
    conn = get_connection()
    query = '''
        SELECT 
            m.id,
            m.data,
            m.tipo_servico,
            m.descricao,
            m.km_realizado,
            m.proximo_servico_km,
            m.proximo_servico_data,
            m.valor,
            v.placa as veiculo_placa,
            v.modelo as veiculo_modelo
        FROM manutencoes m
        JOIN veiculos v ON m.veiculo_id = v.id
        ORDER BY m.data DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def delete_maintenance(maintenance_id):
    """Deletes a maintenance record."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM manutencoes WHERE id = ?", (maintenance_id,))
        conn.commit()
        return True, "Manutenção excluída com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir manutenção: {e}"
    finally:
        conn.close()

def get_maintenance_alerts():
    """Returns a DataFrame of vehicles approaching maintenance."""
    conn = get_connection()
    # Logic: Vehicles where current km is close to next service km (e.g., within 1000km)
    # or next service date is close/passed.
    # For simplicity, let's fetch all vehicles with their latest maintenance info and filter in Python or complex SQL.
    # Here we'll do a query to get vehicles and their max next_service_km.
    
    query = '''
        SELECT 
            v.id,
            v.placa,
            v.modelo,
            v.km_atual,
            MAX(m.proximo_servico_km) as proximo_servico_km,
            MAX(m.proximo_servico_data) as proximo_servico_data
        FROM veiculos v
        LEFT JOIN manutencoes m ON v.id = m.veiculo_id
        GROUP BY v.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Filter for alerts (e.g., within 1000km or date passed)
    alerts = []
    for index, row in df.iterrows():
        if pd.notna(row['proximo_servico_km']):
            km_diff = row['proximo_servico_km'] - row['km_atual']
            if km_diff <= 1000: # Alert if within 1000km or overdue
                alerts.append(row)
    
    if alerts:
        return pd.DataFrame(alerts)
    return pd.DataFrame()


# ============ FUEL / ABASTECIMENTO FUNCTIONS ============

def add_abastecimento(veiculo_id, identificacao, numero_frota, data,
                      tipo_combustivel, volume_litros, preco_litro,
                      valor_total, km_anterior, km_atual_bomba, lote_importacao=None):
    """Inserts a fuel record and updates vehicle km."""
    km_rodados = km_atual_bomba - km_anterior if km_anterior and km_anterior > 0 else None
    rendimento = round(km_rodados / volume_litros, 2) if km_rodados and volume_litros > 0 else None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO abastecimentos
                (veiculo_id, identificacao, numero_frota, data, tipo_combustivel,
                 volume_litros, preco_litro, valor_total, km_anterior, km_atual,
                 km_rodados, rendimento_kml, lote_importacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (veiculo_id, identificacao, numero_frota, data, tipo_combustivel,
              volume_litros, preco_litro, valor_total, km_anterior, km_atual_bomba,
              km_rodados, rendimento, lote_importacao))
        # Update vehicle km if new km > current
        if veiculo_id:
            cursor.execute(
                "UPDATE veiculos SET km_atual = ? WHERE id = ? AND km_atual < ?",
                (km_atual_bomba, veiculo_id, km_atual_bomba)
            )
        conn.commit()
        return True, rendimento
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_abastecimentos(veiculo_id=None, data_inicio=None, data_fim=None):
    """Returns fuel records, optionally filtered."""
    conn = get_connection()
    query = '''
        SELECT
            a.id, a.data, a.identificacao, a.numero_frota,
            a.tipo_combustivel, a.volume_litros, a.preco_litro,
            a.valor_total, a.km_anterior, a.km_atual, a.km_rodados,
            a.rendimento_kml, a.lote_importacao,
            COALESCE(v.placa, a.identificacao) as placa,
            COALESCE(v.modelo, '—') as modelo,
            a.veiculo_id
        FROM abastecimentos a
        LEFT JOIN veiculos v ON a.veiculo_id = v.id
    '''
    conditions = []
    params = []
    if veiculo_id:
        conditions.append("a.veiculo_id = ?")
        params.append(veiculo_id)
    if data_inicio:
        conditions.append("a.data >= ?")
        params.append(data_inicio)
    if data_fim:
        conditions.append("a.data <= ?")
        params.append(data_fim)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY a.data DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_fleet_fuel_summary():
    """Returns a summary of fuel efficiency per vehicle."""
    conn = get_connection()
    query = '''
        SELECT
            COALESCE(v.placa, a.identificacao) as placa,
            COALESCE(v.modelo, '—') as modelo,
            COALESCE(v.numero_frota, a.numero_frota) as frota,
            COALESCE(v.tipo_combustivel, a.tipo_combustivel) as combustivel,
            v.km_atual,
            COUNT(a.id) as total_abastecimentos,
            SUM(a.volume_litros) as total_litros,
            SUM(a.valor_total) as total_gasto,
            AVG(CASE WHEN a.rendimento_kml > 0 THEN a.rendimento_kml END) as media_rendimento,
            MIN(CASE WHEN a.rendimento_kml > 0 THEN a.rendimento_kml END) as min_rendimento,
            MAX(CASE WHEN a.rendimento_kml > 0 THEN a.rendimento_kml END) as max_rendimento,
            SUM(a.km_rodados) as total_km_rodados
        FROM abastecimentos a
        LEFT JOIN veiculos v ON a.veiculo_id = v.id
        GROUP BY COALESCE(v.id, a.identificacao)
        ORDER BY total_gasto DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ============ MAINTENANCE PLAN FUNCTIONS ============

INTERVALOS_PADRAO = {
    'flex': {
        'Troca de Óleo + Filtro': {'km': 10000, 'dias': 180, 'prioridade': 'critica'},
        'Filtro de Ar':           {'km': 15000, 'dias': 365, 'prioridade': 'normal'},
        'Filtro de Combustível':  {'km': 20000, 'dias': 365, 'prioridade': 'normal'},
        'Revisão Geral':          {'km': 20000, 'dias': 365, 'prioridade': 'critica'},
        'Freios':                 {'km': 30000, 'dias': 540, 'prioridade': 'critica'},
        'Troca de Pneus':         {'km': 40000, 'dias': 730, 'prioridade': 'normal'},
        'Correia Dentada':        {'km': 60000, 'dias': 1460,'prioridade': 'critica'},
    },
    'diesel': {
        'Troca de Óleo + Filtro': {'km': 5000,  'horas': 250,  'dias': 180, 'prioridade': 'critica'},
        'Filtro de Ar':           {'km': 10000, 'horas': 500,  'dias': 365, 'prioridade': 'normal'},
        'Filtro de Combustível':  {'km': 10000, 'horas': 500,  'dias': 365, 'prioridade': 'normal'},
        'Revisão Geral':          {'km': 15000, 'horas': 750,  'dias': 365, 'prioridade': 'critica'},
        'Freios':                 {'km': 30000, 'dias': 540,                'prioridade': 'critica'},
        'Troca de Pneus':         {'km': 50000, 'dias': 730,                'prioridade': 'normal'},
        'Correia / Corrente':     {'horas': 2000,'dias': 1460,              'prioridade': 'critica'},
    }
}


def upsert_maintenance_plan(veiculo_id, tipo_servico, intervalo_km=None,
                             ultima_km=None, proxima_km=None,
                             intervalo_horas=None, ultima_horas=None, proxima_horas=None,
                             intervalo_dias=None, ultima_data=None, proxima_data=None,
                             prioridade='normal'):
    """Creates or updates a maintenance plan entry."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM planos_manutencao WHERE veiculo_id=? AND tipo_servico=?",
            (veiculo_id, tipo_servico)
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute('''
                UPDATE planos_manutencao SET
                    intervalo_km=?, ultima_km=?, proxima_km=?,
                    intervalo_horas=?, ultima_horas=?, proxima_horas=?,
                    intervalo_dias=?, ultima_data=?, proxima_data=?,
                    prioridade=?, ativo=1
                WHERE veiculo_id=? AND tipo_servico=?
            ''', (intervalo_km, ultima_km, proxima_km,
                  intervalo_horas, ultima_horas, proxima_horas,
                  intervalo_dias, ultima_data, proxima_data,
                  prioridade, veiculo_id, tipo_servico))
        else:
            cursor.execute('''
                INSERT INTO planos_manutencao
                    (veiculo_id, tipo_servico, intervalo_km, ultima_km, proxima_km,
                     intervalo_horas, ultima_horas, proxima_horas,
                     intervalo_dias, ultima_data, proxima_data, prioridade)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (veiculo_id, tipo_servico, intervalo_km, ultima_km, proxima_km,
                  intervalo_horas, ultima_horas, proxima_horas,
                  intervalo_dias, ultima_data, proxima_data, prioridade))
        conn.commit()
        return True, "Plano salvo!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_maintenance_plans(veiculo_id):
    """Returns all maintenance plans for a vehicle."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM planos_manutencao WHERE veiculo_id=? AND ativo=1 ORDER BY prioridade DESC",
        conn, params=(veiculo_id,)
    )
    conn.close()
    return df


def get_fleet_health():
    """Returns maintenance status for all vehicles with plans."""
    conn = get_connection()
    query = '''
        SELECT
            v.id, v.placa, v.modelo, v.km_atual, v.hodometro_horas,
            v.tipo_combustivel, v.numero_frota,
            p.tipo_servico, p.proxima_km, p.proxima_horas, p.proxima_data, p.prioridade
        FROM veiculos v
        LEFT JOIN planos_manutencao p ON v.id = p.veiculo_id AND p.ativo = 1
        ORDER BY v.placa, p.prioridade DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def count_critical_alerts():
    """Returns count of vehicles with overdue or urgent maintenance."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(DISTINCT p.veiculo_id)
            FROM planos_manutencao p
            JOIN veiculos v ON v.id = p.veiculo_id
            WHERE p.ativo = 1 AND (
                (p.proxima_km IS NOT NULL AND v.km_atual >= p.proxima_km - 500) OR
                (p.proxima_horas IS NOT NULL AND v.hodometro_horas >= p.proxima_horas - 20)
            )
        ''')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0
