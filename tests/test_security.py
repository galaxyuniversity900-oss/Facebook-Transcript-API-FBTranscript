import pytest
from fbtranscript.security import validate_facebook_url

@pytest.mark.parametrize("url", [
 "https://www.facebook.com/watch/?v=123",
 "https://m.facebook.com/video.php?v=123",
 "https://fb.watch/abc123/",
])
def test_accepts_facebook_urls(url):
 assert validate_facebook_url(url) == url

@pytest.mark.parametrize("url", [
 "https://example.com/video", "file:///etc/passwd",
 "https://facebook.com.evil.example/video", "javascript:alert(1)",
])
def test_rejects_non_facebook_urls(url):
 with pytest.raises(ValueError):
  validate_facebook_url(url)
