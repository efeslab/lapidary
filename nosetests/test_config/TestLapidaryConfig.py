from lapidary.config import *

from tempfile import NamedTemporaryFile

data =  '''
        gem5_path: ../custom_gem5
        gem5_features:
            syscall_trace: true

        libc_path: ../libc/glibc/build/install
        '''

def test_init_rawdata():
    config = LapidaryConfig(rawdata=data)
    assert config is not None
    assert len(config.elements) == 3

def test_bad_init():
    try:
        LapidaryConfig(rawdata='')
        raise Exception('Should fail with an empty string!')
    except ConfigException:
        return

def test_file_init():
    with NamedTemporaryFile(mode='w') as f:
        f.write(data)
        f.flush()
        config = LapidaryConfig(filename=f.name)
        assert config is not None
        assert len(config.elements) == 3

        assert isinstance(config.elements['gem5_features'], dict)
        assert isinstance(config.elements['gem5_features']['syscall_trace'], 
                          bool)
