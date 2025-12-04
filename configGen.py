import json
import os

# --- Ayarlar ---
NODE_LIST = ["node_A", "node_B", "node_C"]
BASE_IP = "10.0.1."
BASE_PUB_PORT = 5551
BASE_SYNC_PORT = 5552
# ---------------

def generate_all_configs():
    
    # 1. Önce tüm peer'lerin tam listesini oluştur
    all_peers_list = []
    for i, nid in enumerate(NODE_LIST):
        all_peers_list.append({
            "id": nid,
            "ip": f"{BASE_IP}{10 + i}",
            "pub_port": BASE_PUB_PORT + (i * 10),
            "sync_port": BASE_SYNC_PORT + (i * 10)
        })

    print(f"{len(NODE_LIST)} adet config dosyası oluşturuluyor...")

    # 2. Şimdi her node için KENDİ config dosyasını oluştur
    for current_node_id in NODE_LIST:
        
        # O node'a özel config içeriği:
        # Tam peer listesi + o node'un kendi ID'si
        config_data = {
            "peers": all_peers_list,
            "my_id": current_node_id  # <--- Her dosya için bu değişecek
        }
        
        # O node'a özel dosya adı
        filename = f"config_{current_node_id}.json"
        
        # Dosyayı yaz
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=2)
            
        print(f"-> {filename} oluşturuldu.")

    print("Tüm config dosyaları tamamlandı.")

if __name__ == "__main__":
    generate_all_configs()