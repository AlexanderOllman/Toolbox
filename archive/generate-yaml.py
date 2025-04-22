
# generate_yaml.py
import sqlite3
import json
import yaml


def load_servers(db_path='mcp_servers.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT name, command, args, description FROM servers')
    rows = c.fetchall()
    conn.close()

    servers = {}
    for name, command, args_json, description in rows:
        args = json.loads(args_json)
        servers[name] = {
            'command': command,
            'args': args
        }
        print(description)
    return servers


def generate_yaml(servers, output_path='mcp_servers.yaml'):
    data = {'mcp': {'servers': servers}}
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, sort_keys=False)
    print(f"Wrote configuration to {output_path}.")


def main():
    servers = load_servers()
    generate_yaml(servers)

if __name__ == '__main__':
    main()
