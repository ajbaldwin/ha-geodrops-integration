def test_package_imports():
    import geodrops_sync
    assert isinstance(geodrops_sync.__version__, str)
