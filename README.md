# Parallel-transfer-file<br>
This is the first version and only implements the basic functions.<br>
    SSL is not used, just unencrypted traffic.<br>
    Only transfer directories and normal files are supported.<br>
    File permission synchronization is not supported.<br>
    No signal processing.<br>
<br>
send_file.py parameter:<br>
  --server: server ip address<br>
  --port: The port to listen on or connect to<br>
  --file: The file or directory to transfer<br>
  --remote_dir: The server store path<br>
  --length: Specifies the data size per transfer in bytes<br>
  --process_num: The number of processes to start, by default, is the number of native CPU cores<br>
  --thread_num: Number of threads per process<br>
  --ip_version: The ip protocol version<br>
<br>
recv_file_file.py parameter:<br>
  --addr: ip address.<br>
  --port: The port to listen<br>
  --ip_ver: The ip protocol version<br>
<br>
examples:<br>
  python3 send_file.py --server x.x.x.x --port xxx --file /path/file --remote_dir /remote_dir/ --process_num 21 --length 157286400 --ip_version 6<br>
  python3 send_file.py --server x.x.x.x --port xxx --file /path/dir --remote_dir /remote_dir/ --length 1572864<br>
  python3 recv_file.py --port xxx --ip_ver 6<br>
