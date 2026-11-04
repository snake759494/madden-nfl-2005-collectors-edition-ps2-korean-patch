"""ONLINE.DAT 오버레이의 DNAS/네트워크 오류 문구 번역표(translation/elf_08_online.tsv) 생성. 번역은 아래 표에 직접 적은 것."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ktext import esc
MSG = {
    'The network authentication server is busy. Please try again later.': '네트워크 인증 서버가 혼잡합니다. 나중에 다시 시도하세요.',
    'This software title is not in service. ': '이 타이틀은 서비스하지 않습니다. ',
    'The network authentication server is not in service.': '네트워크 인증 서버가 서비스 중이 아닙니다.',
    'Connection to the network authentication server has timed out. Please try again later.': '네트워크 인증 서버 연결 시간이 초과되었습니다. 나중에 다시 시도하세요.',
    'A network authentication system error has occurred.': '네트워크 인증 시스템 오류가 발생했습니다.',
    'Network connection has been aborted.': '네트워크 연결이 중단되었습니다.',
    'Error in proxy setting.': '프록시 설정 오류입니다.',
    'Connection timed out. Please try connecting again at a later time.': '연결 시간이 초과되었습니다. 나중에 다시 연결하세요.',
    'Connection to the DNAS server failed.': 'DNAS 서버 연결에 실패했습니다.',
    'There was an error in the response from the DNS server. Please check your network configuration.': 'DNS 서버 응답에 오류가 있습니다. 네트워크 설정을 확인하세요.',
    'There was no response from the DNS server. Please check your network configuration.': 'DNS 서버가 응답하지 않습니다. 네트워크 설정을 확인하세요.',
    'There was a DNS error. Please check your network configuration.': 'DNS 오류입니다. 네트워크 설정을 확인하세요.',
    'There was a connection error.': '연결 오류가 발생했습니다.',
    'An authentication error has occurred. ': '인증 오류가 발생했습니다. ',
}
DNAS = {101: 0, 102: 1, 103: 1, 104: 2, 105: 3, 106: 4, 107: 4, 108: 4}
NET = {601: 5, 602: 6, 603: 7, 610: 8, 611: 9, 612: 10, 613: 9, 614: 9, 615: 11, 616: 8, 617: 7,
       618: 8, 619: 8, 620: 8, 621: 12, 622: 12, 623: 12, 624: 12, 625: 12, 626: 8}
keys = list(MSG)
rows = []
for code, k in DNAS.items():
    rows.append(('DNAS Error (-%d)\n%s' % (code, keys[k]), 'DNAS 오류 (-%d)\n%s' % (code, MSG[keys[k]])))
for code, k in NET.items():
    rows.append(('Network Error (-%d)\n%s' % (code, keys[k]), '네트워크 오류 (-%d)\n%s' % (code, MSG[keys[k]])))
rows.append(('DNAS Error (-xxx)\nAn authentication error has occurred. ', 'DNAS 오류 (-xxx)\n인증 오류가 발생했습니다. '))
rows += [
    ('Operation Cancelled by User', '사용자가 작업을 취소함'),
    ('Unknown Client Error', '알 수 없는 클라이언트 오류'),
    ("Please write down the error code number, and contact SCEA at 1-866-466-5333 or via SCEA's website, www.us.playstation.com.",
     '오류 코드 번호를 적어 두고 SCEA(1-866-466-5333, www.us.playstation.com)에 문의하세요.'),
    ('Please check the start and end dates for this online title at Central Station using the Network Access Disc or refer to PlayStation.com.',
     '네트워크 접속 디스크로 Central Station에 들어가거나 PlayStation.com에서 이 타이틀의 온라인 서비스 기간을 확인하세요.'),
    ('Please go to Central Station using the Network Access Disc for more information, or refer to PlayStation.com.',
     '자세한 내용은 네트워크 접속 디스크로 Central Station에 들어가거나 PlayStation.com을 참고하세요.'),
    ('If you continue to experience the same problem please contact your local PlayStation Customer Care line on the number provided in the software manual.',
     '같은 문제가 계속되면 설명서에 적힌 PlayStation 고객 센터로 문의하세요.'),
    ('Please contact your local PlayStation Customer Care line on the number provided in the software manual for assistance.',
     '설명서에 적힌 PlayStation 고객 센터로 문의하세요.'),
    ('Try cleaning the disc using an approved method as detailed on Central Station (access using Network Access Disc)\nand PlayStation.com. If the problem continues to occur please contact your local PlayStation Customer Care line on the number provided in the software manual.',
     'Central Station(네트워크 접속 디스크로 접속)과 PlayStation.com에 안내된 방법으로\n디스크를 닦아 보세요. 문제가 계속되면 설명서에 적힌 PlayStation 고객 센터로 문의하세요.'),
]
out = os.path.join(HERE, '..', 'translation', 'elf_08_online.tsv')
with open(out, 'w', encoding='utf-8', newline='\n') as f:
    f.write('# ONLINE.DAT 오버레이(온라인 모듈) DNAS/네트워크 오류 문구 - tools/gen_online_tsv.py 로 생성\n')
    for en, ko in rows: f.write(esc(en) + '\t' + esc(ko) + '\n')
print(len(rows))
