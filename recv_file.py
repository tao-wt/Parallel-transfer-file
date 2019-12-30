import os
import sys
import time
import multiprocessing
import hashlib
import argparse
import socket
import logging


def auto_next(func):
    def start(*args, **kwargs):
        g = func(*args, **kwargs)
        g.__next__()
        return g
    return start


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


def recv_raw(sockfd, size):
    buf  = 8192
    data = b''
    left_size = size
    while left_size > 0:
        if left_size < 8192:
            buf  = left_size
        data = sockfd.recv(buf)
        if not data:
            break
        yield data
        left_size -= len(data)
    return None


def set_sock_opt(sockfd):
    sockfd.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )


def create_files(sfd, addr):
    file_len = int(recv(sfd, 6))
    files = str(
        recv(sfd, file_len),
        encoding='utf-8'
    ).split('\n')
    log.debug(files)
    result = True
    for file in files:
        if not file:
            continue
        if os.path.exists(file):
            log.info(
                '{}: rename old file {}'.format(
                    addr,
                    file
                )
            )
            os.rename(
                file,
                '{}_{}'.format(file, time.time())
            )
        log.info(
            '{}: create file {}'.format(
                addr,
                file
            )
        )
        try:
            fd = open(file, mode="wb")
            fd.close()
        except Exception:
            log.info(
                '{}: create file {} error'.format(
                    addr,
                    dir
                )
            )
            result = False
            break
    if result:
        send(sfd, b'0')
    else:
        send(sfd, b'1')


def create_dirs(sfd, addr):
    dir_len = int(recv(sfd, 6))
    dirs = str(
        recv(sfd, dir_len),
        encoding='utf-8'
    ).split('\n')
    log.debug(dirs)
    result = True
    for dir in dirs:
        if not dir:
            continue
        if not os.path.exists(dir):
            log.info(
                '{}: create dir {}'.format(
                    addr,
                    dir
                )
            )
            try:
                os.mkdir(dir)
            except Exception:
                log.info(
                    '{}: create dir {} error'.format(
                        addr,
                        dir
                    )
                )
                result = False
                break
    if result:
        send(sfd, b'0')
    else:
        send(sfd, b'1')


def write_file(sfd, addr):
    md5 = hashlib.md5()
    file_len = int(recv(sfd, 6))
    file = str(recv(sfd, file_len), encoding='utf-8')
    offset = int(recv(sfd, 12))
    size = int(recv(sfd, 12))
    log.info(
        '{}: {}, {}, {}'.format(
            addr,
            file,
            offset,
            size
        )
    )
    fd = os.open(file, os.O_WRONLY)
    os.lseek(fd, offset, 0)
    for data in recv_raw(sfd, size):
        md5.update(data)
        os.write(fd, data)
    os.close(fd)
    md5_value = bytes(
        md5.hexdigest(),
        encoding='utf-8'
    )
    send(sfd, md5_value)


def recv_process(sfd, addr):
    log.info("{}: connected.".format(addr))
    while True:
        log.info("{}: waiting data".format(addr))
        op = str(recv(sfd, 2), encoding='utf-8')
        if not op:
            break
        if op == "wf":
            log.info("{}: write file".format(addr))
            write_file(sfd, addr)
        elif op == 'cd':
            log.info("{}: create dir".format(addr))
            create_dirs(sfd, addr)
        elif op == 'cf':
            log.info("{}: create file".format(addr))
            create_files(sfd, addr)
        else:
            log.info(
                '{}: action {} error, close connect.'.format(
                    addr,
                    op
                )
            )
            break
        log.info("{}: {} process ok".format(addr, op))
    sfd.close()
    log.info("{}: process finish.".format(addr))


def parse_arguments():
    '''
    get args
    '''
    parse = argparse.ArgumentParser()
    parse.add_argument('--ip_ver', type=int, help='4/6')
    parse.add_argument('--addr', help='listen ip')
    parse.add_argument(
        '--port',
        required=True,
        type=int,
        help='listen port'
    )
    args = parse.parse_args()
    return args


if __name__ == "__main__":
    args = parse_arguments()
    log = setup_logger(debug="True")
    if args.ip_ver and args.ip_ver == 4:
        sockfd = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        addr = args.addr if args.addr else '0.0.0.0'
    else:
        if not socket.has_ipv6:
            log.error("Not support IPv6!")
            sys.exit(1)
        sockfd = socket.socket(
            socket.AF_INET6,
            socket.SOCK_STREAM
        )
        addr = args.addr if args.addr else '::'
    set_sock_opt(sockfd)
    sockfd.bind((addr, args.port))
    sockfd.listen(5)
    log.info(
        "start accept connection on {}".format(
            args.port
        )
    )
    while True:
        cli, addr = sockfd.accept()
        p = multiprocessing.Process(
            target=recv_process,
            args=(cli, addr,)
        )
        p.start()
