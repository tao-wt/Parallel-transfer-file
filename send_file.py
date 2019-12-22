import os
import sys
import re
import threading
import multiprocessing
import hashlib
import argparse
import socket
import logging


def setup_logger(debug="False"):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s:\t%(module)s@%(lineno)s:\t%(message)s'
    )
    ch = logging.StreamHandler()
    if debug.lower() == "true":
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.WARNING)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def send(sockfd, data):
    send_size = 0
    while send_size < len(data):
        send_size += sockfd.send(data[send_size:])


def recv(sockfd, size):
    result = b''
    left_size = size
    while left_size > 0:
        data = sockfd.recv(left_size)
        if not data:
            break
        result = result + data
        left_size = size - len(result)
    return result


def set_sock_opt(sockfd):
    pass


class send_thread(threading.Thread):
    def __init__(self, server, queue, remote_dir, name):
        threading.Thread.__init__(self)
        self.queue = queue
        self.server = server
        self.name = name
        self.remote_dir = remote_dir
        self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        set_sock_opt(self.sockfd)
        self.sockfd.connect(self.server)
        self.sock_name = self.sockfd.getsockname()
        self.deamon = True

    def init_conn(self):
        file_bytes = bytes(
            os.path.join(self.remote_dir, re.sub(r'^./', '', self.file)),
            encoding='utf-8'
        )
        name_length_str = str(len(file_bytes))
        if len(name_length_str) <= 6:
            name_length_str = "0" * (6 - len(name_length_str)) + name_length_str
        else:
            log.info('file {} too long!')
            sys.exit(2)

        size_str = str(self.size)
        if len(size_str) <= 12:
            size_str = "0" * (12 - len(size_str)) + size_str
        else:
            log.info('data size {} too long!')
            sys.exit(2)

        offset_str = str(self.offset)
        if len(offset_str) <= 12:
            offset_str = "0" * (12 - len(offset_str)) + offset_str
        else:
            log.info('offset {} too long!')
            sys.exit(2)

        data = b'wf' \
                + bytes(name_length_str, encoding='utf-8') \
                + file_bytes \
                + bytes(offset_str, encoding='utf-8') \
                + bytes(size_str, encoding='utf-8')
        send(self.sockfd, data)

    def send_data(self):
        self.init_conn()
        retry = 0
        while retry < 3:
            retry += 1
            md5 = hashlib.md5()
            buf = 8192
            left_size = self.size
            with open(self.file, 'rb') as f:
                f.seek(self.offset)
                while left_size > 0:
                    if left_size < 8192:
                        buf = left_size
                        left_size = 0
                    else:
                        left_size -= buf
                    data = f.read(buf)
                    if not data:
                        break
                    md5.update(data)
                    send(self.sockfd, data)
            # self.sockfd.shutdown(1)
            md5_value = md5.hexdigest()
            if self.check_result(md5_value):
                break

    def run(self):
        log.info("{} start".format(self.name))
        while True:
            file = self.queue.get()
            if file is None:
                break
            self.file, self.offset, self.size = file
            log.info("{} {}: process {}, {}, {}".format(
                self.name,
                self.sock_name,
                self.file,
                self.offset,
                self.size)
            )
            self.send_data()
            log.info("{} {}: process {}, {}, {} done".format(
                self.name,
                self.sock_name,
                self.file,
                self.offset,
                self.size)
            )
        self.sockfd.close()
        log.info("{} end".format(self.name))

    def check_result(self, md5_value):
        data = recv(self.sockfd, 32)
        if not data:
            return False
        data_str = str(data, encoding='utf-8')
        result = True
        if data_str != md5_value:
            result = False
        log.info("{} {}: process {}, {}, {} md5 {}".format(
            self.name,
            self.sock_name,
            self.file,
            self.offset,
            self.size,
            result)
        )
        return result


def send_process(server, get_queue, thread_num, remote_dir, name):
    log.info("{} start".format(name))
    thread_list = list()
    for loop in range(0, thread_num):
        thread_name = "{}_{}>".format(name, loop)
        thread = send_thread(
            server,
            get_queue,
            remote_dir,
            thread_name
        )
        thread.start()
        thread_list.append(thread)

    for thread in thread_list:
        thread.join()
    log.info("{} end".format(name))


def parse_arguments():
    '''
    get args
    '''
    parse = argparse.ArgumentParser()
    parse.add_argument(
        '--server',
        required=True,
        help='server ip/name'
    )
    parse.add_argument(
        '--port',
        required=True,
        type=int,
        help='server port'
    )
    parse.add_argument(
        '--file',
        required=True,
        help='file or dir'
    )
    parse.add_argument(
        '--remote_dir',
        required=True,
        help='remote dest dir'
    )
    parse.add_argument(
        '--length',
        required=True,
        type=int,
        help='Specifies the data size per transfer in bytes'
    )
    parse.add_argument(
        '--process_num',
        type=int,
        help='process num'
    )
    parse.add_argument(
        '--thread_num',
        type=int,
        help='Number of threads per process'
    )
    args = parse.parse_args()
    return args


def generate_queue_item(queue, files):
    for file in files:
        stat_obj = os.stat(file)
        for offset in range(0, stat_obj.st_size, args.length):
            length = args.length
            if args.length + offset > stat_obj.st_size:
                length = stat_obj.st_size - offset
            log.debug((file, offset, length))
            queue.put((file, offset, length))
    for i in range(0, args.process_num * args.thread_num):
        queue.put(None)


def get_file_list():
    f_list = list()
    f_data = b''
    d_data = b''
    for root, dirs, files in os.walk(".", topdown=True):
        for name in files:
            f_list.append(os.path.join(root, name))
            rem_str = bytes(
                os.path.join(
                    args.remote_dir,
                    re.sub(r'^./', '', os.path.join(root, name))
                ),
                encoding='utf-8'
            )
            f_data += rem_str + b'\n'
        for name in dirs:
            rem_str = bytes(
                os.path.join(
                    args.remote_dir,
                    re.sub(r'^./', '', os.path.join(root, name))
                ),
                encoding='utf-8'
            )
            d_data += rem_str + b'\n'
    return f_list, f_data, d_data


def init_remote_env():
    f_len_str = bytes(str(len(file_data)), encoding='utf-8')
    d_len_str = bytes(str(len(dir_data)), encoding='utf-8')
    if len(f_len_str) > 6 or len(d_len_str) > 6:
        log.info('files {} too long!')
        sys.exit(1)
    init_sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    init_sockfd.connect(server)
    sock_name = init_sockfd.getsockname()
    file_str = b'cf' + b'0' * (6 - len(f_len_str)) + f_len_str + file_data
    dir_str = b'cd' + b'0' * (6 - len(d_len_str)) + d_len_str + dir_data
    log.debug(file_str+dir_str)
    send(init_sockfd, dir_str)
    result = str(recv(init_sockfd, 1), encoding='utf-8')
    if result != '0':
        log.error("{}: create dir error {}.".format(sock_name, result))
        sys.exit(1)
    log.info("dirs create ok.")
    send(init_sockfd, file_str)
    result = str(recv(init_sockfd, 1), encoding='utf-8')
    if result != '0':
        log.error("{}: create file error.".format(sock_name, result))
        sys.exit(1)
    log.info("files create ok.")
    init_sockfd.close()


if __name__ == "__main__":
    args = parse_arguments()
    log = setup_logger(debug="True")
    server = (args.server, args.port)
    args.file = args.file.strip()
    if os.path.isdir(args.file):
        log.info("{} is a directory".format(args.file))
        os.chdir(args.file)
        args.file, file_data, dir_data = get_file_list()
        dir_data = bytes(args.remote_dir, encoding='utf-8') \
            + b'\n' \
            + dir_data
    elif os.path.isfile(args.file):
        log.info("{} is a normal file".format(args.file))
        if '/' in args.file:
            os.chdir('/'.join(args.file.split('/')[:-1]))
        file_name = os.path.basename(args.file)
        args.file = [file_name]
        file_data = bytes(
            os.path.join(args.remote_dir, file_name),
            encoding='utf-8'
        )
        dir_data = bytes(args.remote_dir, encoding='utf-8')
    else:
        log.info("Error {} is a special file".format(args.file))
        sys.exit(1)

    init_remote_env()

    queue = multiprocessing.Queue()
    if not args.thread_num:
        args.thread_num = 3
    if not args.process_num:
        args.process_num = multiprocessing.cpu_count()

    process_list = list()
    for loop in range(0, args.process_num):
        process = multiprocessing.Process(
            target=send_process,
            args=(
                server,
                queue,
                args.thread_num,
                args.remote_dir, "process_{}".format(loop)
            )
        )
        process.deamon = True
        process.start()
        process_list.append(process)

    generate_queue_item(queue, args.file)

    for process in process_list:
        process.join()

    log.info('Send {} finish.'.format(args.file))
