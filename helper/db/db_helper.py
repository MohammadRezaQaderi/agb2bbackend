def insert_value(conn, cursor, table_name, fields, values, id_column=None):
    """
    Inserts a record into the given table and optionally returns the new record's ID.

    Args:
        conn: Active DB connection
        cursor: Active cursor
        table_name (str): Name of the target table
        fields (str): Fields in SQL insert format, e.g., '([name], [phone])'
        values (tuple): Values to insert
        id_column (str, optional): The name of the ID column (to fetch inserted ID)

    Returns:
        dict: Contains 'id' if requested, otherwise True/None on success
    """
    try:
        inserted_id = None
        if id_column:
            sql_script = f"""
                INSERT INTO {table_name} {fields}
                OUTPUT INSERTED.{id_column}
                VALUES ({", ".join(["?"] * len(values))})
            """
            cursor.execute(sql_script, values)
            inserted_id = cursor.fetchone()[0]
        else:
            sql_script = f'INSERT INTO {table_name} {fields} VALUES ({", ".join(["?"] * len(values))})'
            cursor.execute(sql_script, values)
        conn.commit()
        return {"id": inserted_id} if id_column else True
    except Exception as e:
        conn.rollback()
        print(f"Error in insert_value for {table_name}: {e}")
        return None


def update_record(conn, cursor, table_name, update_fields, update_values, condition, condition_values):
    try:
        set_clause = ", ".join(f"{field} = ?" for field in update_fields)
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
        params = update_values + condition_values
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        print(f"Error updating record: {e}")
        return 0


def delete_record(conn, cursor, table_name, condition_fields, condition_values):
    try:
        where_clause = " AND ".join(f"{field} = ?" for field in condition_fields)
        sql = f"DELETE FROM {table_name} WHERE {where_clause}"
        cursor.execute(sql, condition_values)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        print(f"Error deleting record: {e}")
        return 0


def search_table(conn, cursor, query, field):
    response = cursor.execute(query, field)
    row = response.fetchone()
    conn.commit()
    return row


def search_allin_table(conn, cursor, query, field):
    response = cursor.execute(query, field)
    res = response.fetchall()
    conn.commit()
    return res


def search_fetchall(conn, cursor, query, field=None):
    """
    Executes a query and returns all rows as a list of dicts.

    Args:
        conn: DB connection
        cursor: DB cursor
        query (str): SQL query (with ? placeholders)
        field (tuple|list|single): Parameters for the query (optional)

    Returns:
        list[dict]: Each row as a dict with column names as keys
    """
    try:
        if field is not None:
            response = cursor.execute(query, (field,) if not isinstance(field, (list, tuple)) else field)
        else:
            response = cursor.execute(query)

        columns = [col[0] for col in cursor.description]
        rows = response.fetchall()
        conn.commit()

        return [dict(zip(columns, row)) for row in rows]

    except Exception as e:
        conn.rollback()
        print(f"Error in search_fetchall: {e}")
        return []
