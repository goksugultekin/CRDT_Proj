import time
from p2p_node import main as _unused  # sadece bağımlılık çözsün diye

# Bu dosyayı örnek olarak bıraktım; gerçek demo için ayrı iki terminalde:
#   python p2p_node.py config_node_A.json
#   python p2p_node.py config_node_B.json
# ardından komut satırından 'move ...' gir.
# Burada çalışır bir “tek süreçte iki node” örneği kurmak yerine
# p2p_node.py’yi üretim akışına uygun bıraktık.
print("Use p2p_node.py with config_node_*.json in two terminals.")
time.sleep(0.5)
