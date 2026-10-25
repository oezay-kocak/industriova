"""Recording stays bounded, survives IO failures, and preserves caller behavior."""
import json
from threading import Event
from time import monotonic, sleep

import pytest

from production_zero.diagnostics.recorder import (
    MAX_METRICS, MAX_TIMING_SAMPLES, PerformanceRecorder, process_memory,
)


def wait_for(predicate, seconds=5):
    until = monotonic()+seconds
    while not predicate() and monotonic()<until:
        sleep(.01)
    assert predicate()


def logs(path):
    return [json.loads(line) for file in path.glob('performance*.jsonl')
            for line in file.read_text(encoding='utf-8').splitlines()]


def test_real_process_sampling_has_valid_windows_memory_and_cpu(tmp_path):
    r = PerformanceRecorder(tmp_path/'run', {'test': True}, interval=.03)
    try:
        r.state({'cards_owned': 900})
        wait_for(lambda:r.summary()['samples']>=2)
    finally:r.close()
    samples=[row for row in logs(r.directory) if row['kind']=='sample']
    assert samples[-1]['game']=={'cards_owned':900}
    assert samples[-1]['cpu_machine_percent']>=0
    if __import__('os').name=='nt':
        assert samples[-1]['rss_bytes']>0 and samples[-1]['private_bytes']>0
        assert samples[-1]['system_ram_total_bytes']>=samples[-1]['system_ram_available_bytes']
    assert json.loads((r.directory/'summary.json').read_text())['closed']
    assert any(row['kind']=='session_ended' for row in logs(r.directory))


def test_ten_hours_worth_of_heartbeat_samples_do_not_accumulate(tmp_path):
    r=PerformanceRecorder(tmp_path/'run',{},interval=3600)
    try:
        for _ in range(10*3600*10):r.heartbeat(.1)
        assert len(r._window['ui_heartbeat_gap']['recent'])==MAX_TIMING_SAMPLES
        assert r._lifetime['ui_heartbeat_gap']['count']==360000
        assert r._queue.qsize()<=1
        for i in range(1000):r.timing('generated-name-'+str(i),.001)
        assert len(r._lifetime)<=MAX_METRICS
        assert len(r._window)<=MAX_METRICS
    finally:r.close()


def test_delayed_ui_has_a_bounded_code_stack_without_local_values(tmp_path):
    r=PerformanceRecorder(tmp_path/'run',{},interval=3600)
    private_local_value='this value must not be included in a diagnostic stack'
    try:
        r._heartbeat_at-=1
        sample=r._sample()
        assert 'test_delayed_ui_has_a_bounded_code_stack' in sample['blocked_ui_stack']
        assert private_local_value not in sample['blocked_ui_stack']
        assert len(sample['blocked_ui_stack'])<=12000
    finally:r.close()


def test_slow_event_storm_is_summarized_and_queues_are_bounded(tmp_path):
    entered,release=Event(),Event()
    def blocked_sample():
        entered.set();assert release.wait(5);return {}
    r=PerformanceRecorder(tmp_path/'run',{},interval=.01,queue_limit=4,memory_sampler=blocked_sample)
    try:
        assert entered.wait(2)
        for i in range(1000):r.event('burst',number=i)
        for _ in range(500):r.timing('simulation',.2)
        assert r._queue.qsize()<=4
        assert r.summary()['dropped_records']>900
        assert r.summary()['suppressed_slow_records']>=480
        assert r._lifetime['simulation']['count']==500
    finally:release.set();r.close()


def test_rotation_keeps_only_four_valid_log_files(tmp_path):
    r=PerformanceRecorder(tmp_path/'run',{},interval=3600,max_log_bytes=600,queue_limit=512)
    for n in range(200):r.event('rotation',number=n,detail='x'*50)
    r.close()
    paths=list(r.directory.glob('performance*.jsonl'))
    assert len(paths)==4
    assert all(p.stat().st_size<=600 for p in paths)
    assert any(row['kind']=='session_ended' for row in logs(r.directory))


def test_measurement_preserves_errors_and_records_context(tmp_path):
    r=PerformanceRecorder(tmp_path/'run',{},interval=3600)
    try:
        with pytest.raises(ValueError,match='original error'):
            with r.span('save_worker'):raise ValueError('original error')
        assert not r._active
        assert r.summary()['timings']['save_worker']['count']==1
    finally:r.close()
    assert any(row['kind']=='operation_error' and row['operation']=='save_worker' for row in logs(r.directory))


def test_disk_failure_does_not_escape_into_game_operations(tmp_path,monkeypatch):
    r=PerformanceRecorder(tmp_path/'run',{},interval=.02)
    def failed(record):raise OSError('test disk full')
    monkeypatch.setattr(r._sink,'write',failed)
    try:
        r.event('trigger')
        wait_for(lambda:r.last_error is not None)
        with r.span('simulation'):value=42
        assert value==42 and 'test disk full' in r.last_error
        assert r._sink is None
    finally:r.close()


def test_copy_report_is_readable_while_background_recording_continues(tmp_path):
    r=PerformanceRecorder(tmp_path/'run',{},interval=.02)
    try:
        wait_for(lambda:r.summary()['samples']>0)
        r.copy_logs(tmp_path/'copy')
        assert json.loads((tmp_path/'copy'/'session.json').read_text())['format']=='industriova-performance-v1'
        assert (tmp_path/'copy'/'summary.json').is_file()
        assert logs(tmp_path/'copy')
        previous=r.summary()['samples'];wait_for(lambda:r.summary()['samples']>previous)
    finally:r.close()
