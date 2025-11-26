import sqlite3
import pandas as pd
import os

DB_NAME = "traffic_app.db"

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

    # Check and add columns if they don't exist (Migration)
    try:
        cursor.execute("ALTER TABLE veiculos ADD COLUMN km_atual REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    try:
        cursor.execute("ALTER TABLE viagens ADD COLUMN distancia REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        cursor.execute("ALTER TABLE multas ADD COLUMN hora_infracao TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        cursor.execute("ALTER TABLE multas ADD COLUMN viagem_id INTEGER REFERENCES viagens(id)")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    conn.commit()
    conn.close()

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

def add_vehicle(placa, modelo, ano, renavam, km_atual=0):
    """Adds a new vehicle to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO veiculos (placa, modelo, ano, renavam, km_atual)
            VALUES (?, ?, ?, ?, ?)
        ''', (placa, modelo, ano, renavam, km_atual))
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

def update_vehicle(vehicle_id, placa, modelo, ano, renavam, km_atual):
    """Updates an existing vehicle's information."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
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
    cursor.execute("SELECT * FROM veiculos WHERE id = ?", (vehicle_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        # Handle cases where km_atual might not exist in old records if not migrated properly, 
        # but init_db handles migration.
        # Structure: id, placa, modelo, ano, renavam, km_atual
        return {
            'id': result[0],
            'placa': result[1],
            'modelo': result[2],
            'ano': result[3],
            'renavam': result[4],
            'km_atual': result[5] if len(result) > 5 else 0
        }
    return None

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

def add_travel(data, motorista_id, veiculo_id, destino, hora_saida, distancia=0):
    """Adds a new travel to the database and updates vehicle mileage."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO viagens (data, motorista_id, veiculo_id, destino, hora_saida, distancia)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data, motorista_id, veiculo_id, destino, hora_saida, distancia))
        
        # Update vehicle mileage
        if distancia > 0:
            cursor.execute('''
                UPDATE veiculos 
                SET km_atual = COALESCE(km_atual, 0) + ?
                WHERE id = ?
            ''', (distancia, veiculo_id))
            
        conn.commit()
        return True, "Viagem cadastrada com sucesso!"
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
            v.destino,
            v.distancia,
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
            'destino': result[4],
            'hora_saida': result[5],
            'distancia': result[6] if len(result) > 6 else 0
        }
    return None

def update_travel(travel_id, data, motorista_id, veiculo_id, destino, hora_saida, distancia):
    """Updates an existing travel's information and adjusts vehicle mileage."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get old distance to adjust vehicle mileage
        cursor.execute("SELECT veiculo_id, distancia FROM viagens WHERE id = ?", (travel_id,))
        old_travel = cursor.fetchone()
        
        if old_travel:
            old_veiculo_id = old_travel[0]
            old_distancia = old_travel[1] if old_travel[1] else 0
            
            # Revert old mileage
            cursor.execute('''
                UPDATE veiculos 
                SET km_atual = km_atual - ?
                WHERE id = ?
            ''', (old_distancia, old_veiculo_id))
            
        cursor.execute('''
            UPDATE viagens 
            SET data = ?, motorista_id = ?, veiculo_id = ?, destino = ?, hora_saida = ?, distancia = ?
            WHERE id = ?
        ''', (data, motorista_id, veiculo_id, destino, hora_saida, distancia, travel_id))
        
        # Add new mileage
        cursor.execute('''
            UPDATE veiculos 
            SET km_atual = km_atual + ?
            WHERE id = ?
        ''', (distancia, veiculo_id))
        
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
