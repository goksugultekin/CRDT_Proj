import json

# --- Ayarlar ---
NODE_LIST = ["node_A", "node_B", "node_C"]
LOOPBACK_IP = "127.0.0.1"         # <<< aynı makinede hepsi localhost
BASE_PUB_PORT = 5551
BASE_SYNC_PORT = 5552
# ---------------

def generate_all_configs():
    # Tüm peer listesi (IP sabit, portlar farklı)
    all_peers_list = []
    for i, nid in enumerate(NODE_LIST):
        all_peers_list.append({
            "id": nid,
            "ip": LOOPBACK_IP,
            "pub_port": BASE_PUB_PORT + (i * 10),
            "sync_port": BASE_SYNC_PORT + (i * 10),
        })

    print(f"{len(NODE_LIST)} adet config dosyası oluşturuluyor...")

    for current_node_id in NODE_LIST:
        config_data = {
            "peers": all_peers_list,
            "my_id": current_node_id,
        }
        filename = f"config_{current_node_id}.json"
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=2)
        print(f"-> {filename} oluşturuldu.")

    print("Tüm config dosyaları tamamlandı.")

if __name__ == "__main__":
    generate_all_configs()
