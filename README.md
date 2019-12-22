# Parallel-transfer-file
This is the first version and only implements the basic functions.
    Only ipv4 IP addresses are supported, does not support ipv6.
    SSL is not used, just unencrypted traffic
    DNS domain resolution is not supported and will be optimized later
    Only transfer directories and normal files are supported
    File permission synchronization is not supported

send_file.py parameter:
  --server: server ip address
  --port: The port to listen on or connect to
  --file: The file or directory to transfer
  --remote_dir: The server store path
  --length: Specifies the data size per transfer in bytes
  --process_num: The number of processes to start, by default, is the number of native CPU cores
  --thread_num: Number of threads per process

recv_file_file.py parameter(The interface value has been specified as 0.0.0.0):
  --port: The port to listen

examples:
  python3 send_file.py --server x.x.x.x --port xxx --file /path/file --remote_dir /remote_dir/ --process_num 21 --length 157286400
  python3 send_file.py --server x.x.x.x --port xxx --file /path/dir --remote_dir /remote_dir/ --length 1572864
  python3 recv_file.py --port xxx
