from src.config import ConfigLoader
import os

def test_config_loader(tmp_path):
    config_content = "api_key: testkey\napi_url: 'http://test/url'\nlive: false"
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    loader = ConfigLoader(str(config_file))
    assert loader.get('api_key') == 'testkey'
    assert loader.get('live') == False
