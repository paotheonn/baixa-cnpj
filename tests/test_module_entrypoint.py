from rf_cnpj import __main__
from rf_cnpj.cli import main


def test_module_entrypoint_reuses_cli_main():
    assert __main__.main is main
