
# KN_DEMO

运行之前请参考这篇文章打开浏览器麦克风权限：https://blog.csdn.net/shiwolf/article/details/129303692

# 部署相关

## 摘要

启动四个 Uvicorn worker 意味着主进程将派生四个 spawn 模式的多进程管理器，每个进程都运行自己的 ASGI 事件循环并监听同一端口，通过操作系统内核的负载均衡策略将传入连接分发到各个 worker，以充分利用多核 CPU 提升并发处理能力。这些 worker 由内置进程管理器监控并在进程意外退出时自动重启，支持平滑增减数量。在每个 worker 内部，通过异步 I/O（`async def` 端点）或线程池（`def` 端点）实现对多个请求的并行处理，从而在单核内也能达成高并发。([uvicorn.org][1], [fastapi.tiangolo.com][2])

## Uvicorn Worker 模型

### 多进程启动（spawn）

* 使用命令行参数 `--workers 4` 会启动 4 个独立的 Uvicorn 进程，每个进程都拥有自己的 Python 解释器与事件循环，且均监听相同端口。([uvicorn.org][1], [uvicorn.org][1])
* 与 Gunicorn 的 pre-fork 不同，Uvicorn 使用 **spawn** 模式来创建子进程，这使得在 Windows 和 Linux 上都能稳定运行。([uvicorn.org][1], [uvicorn.org][1])

### 进程管理与自动重启

* 内置的多进程管理器会监控所有子进程的存活状态，当某个 worker 意外退出或卡死时会自动重启，以保证服务的高可用性。([uvicorn.org][1], [medium.com][3])
* 支持通过发送信号动态增减 worker 数量，例如 Linux 下可用 `SIGHUP` 重启、`SIGTTIN` 增加、`SIGTTOU` 减少子进程。([uvicorn.org][1])

## Worker 内部的并发处理

### 异步 I/O（`async def`）

* 对于使用 `async def` 定义的路径操作，FastAPI/Uvicorn 在同一事件循环中多路复用 I/O 操作，使单个 worker 在没有阻塞调用时即可同时处理数百到上千个并发连接。([reddit.com][4], [github.com][5])

### 线程池执行（`def`）

* 若路径操作使用同步函数（`def`），FastAPI 会将其移交给内部线程池执行，从而防止阻塞事件循环，也能实现并行请求处理。([github.com][5])

## 对请求与性能的影响

### 操作系统层面的负载均衡

* 所有 worker 进程共享同一个监听 socket，操作系统内核会采用 round-robin 或其他策略将新 TCP 连接分发给任意一个就绪进程，从而实现请求的分散处理。([fastapi.tiangolo.com][2], [fastapi.tiangolo.com][2])

### CPU 利用与 GIL 绕过

* 多进程模式可利用多核 CPU 资源，绕过 Python GIL 限制，尤其对 CPU 密集型任务有显著提升；而 I/O 密集型场景下，单进程异步已能高效并发，多 worker 可进一步提升可用性与资源隔离。([medium.com][6], [medium.com][3])

### 并发控制与限流

* Uvicorn 允许配置最大并发任务数（`--backlog` 或服务器行为设置），超出时可返回 503，帮助防止过度并发造成资源耗尽。([uvicorn.org][7])

## 考量与最佳实践

### 合理选择 worker 数量

* 常见经验公式：

  > worker 数 ≈ CPU 核心数 × (1 + 平均等待时间/平均处理时间)
* 过多 worker 会带来额外内存开销，过少则无法充分利用多核。([medium.com][6])

### 避免阻塞调用

* 在异步端点避免使用耗时的同步库（如 `requests`、同步 ORM），改用对应的异步客户端（如 `httpx.AsyncClient`、`asyncpg`），以免事件循环被阻塞而丧失高并发优势。([medium.com][6])

### 在容器化和编排环境中

* 在 Docker/Kubernetes 中，常建议 **每个容器运行单个** Uvicorn 进程，通过容器编排（Horizontal Pod Autoscaler）来扩展；多 worker 容器内多进程方式对诊断、监控和资源限额管理不如外部编排灵活。([fastapi.tiangolo.com][2])

[1]: https://www.uvicorn.org/deployment/?utm_source=chatgpt.com "Deployment - Uvicorn"
[2]: https://fastapi.tiangolo.com/deployment/server-workers/?utm_source=chatgpt.com "Server Workers - Uvicorn with Workers - FastAPI"
[3]: https://medium.com/%40niteeshboddapu/understanding-uvicorn-and-how-gunicorn-enhances-it-4ef46261886e?utm_source=chatgpt.com "Understanding Uvicorn and How Gunicorn Enhances It - Medium"
[4]: https://www.reddit.com/r/FastAPI/comments/1dkpu11/does_uvicorn_handle_multiple_requests_at_once/?utm_source=chatgpt.com "Does uvicorn handle multiple requests at once? Confused ... - Reddit"
[5]: https://github.com/tiangolo/fastapi/discussions/4358?utm_source=chatgpt.com "Unexpected fastapi + uvicorn concurrency #4358 - GitHub"
[6]: https://medium.com/%40aahana.khanal11/scaling-a-fastapi-application-handling-multiple-requests-at-once-e5c128720c95?utm_source=chatgpt.com "Scaling a FastAPI Application: Handling Multiple Requests at Once"
[7]: https://www.uvicorn.org/server-behavior/?utm_source=chatgpt.com "Server Behavior - Uvicorn"

# 技术细节

## 音频接口类单例

单例不等于单连接：单例 session 只是共用同一个连接池，真正的并发度由 connector.limit（以及系统的 file-descriptor 限制）决定。

安全高效：一个 ClientSession 就能管理成百上千并发请求，无需为每一次请求都 Session()/close()。

## 音频接口的长连接

`keepalive_timeout=300` 这行的作用，其实就是告诉 aiohttp 在它的连接池里：对于已经建立好的 TCP 长连接，如果空闲（也就是没有正在传输请求/响应）超过 300 秒，就自动关闭它；但如果在这 5 分钟内又来了新请求，就直接复用这个「热」连接，而不用重新走 DNS→TCP→TLS 握手。

- 减少握手开销

默认情况下，aiohttp 的连接空闲超时只有 15 秒（keepalive_timeout=15），15 秒后就关掉，不再复用。把它调到 300 秒，就能在 5 分钟内多次重用，同一条 TCP/TLS 连接可以承载多次 HTTP 请求，大幅降低新建连接的开销。

- 应对突发流量

如果你的服务有「一分钟内多次调用同一个后端」的场景，比如批量转录或者短时间内多音频上传，长连接能保证后续请求都是「秒级直连」，整体延迟降到最低。

- 资源自动回收

5 分钟后如果真的没人再用，连接池会自己清理掉这些空闲连接，避免占用无用的文件描述符或让后端保持过多 TCP 连接。

### 区别于操作系统层面的 TCP Keep-Alive

操作系统 TCP Keep-Alive：通常是 OS 在连接完全空闲（没有任何应用层数据收发）数小时后，才会发探测包，跟我们这里的“连接池空闲”不是一回事。

aiohttp 连接池的 keepalive_timeout：应用层面、HTTP 客户端自己管理的“空闲回收”时长，更灵活，也更贴合 HTTP 请求的生命周期。

### 什么时候调短或调长？

- 高 QPS、反复调用同一主机：时间可以设长一点（如 5–10 分钟），让热点连接更持久。

- 低调用频率或后端不希望大量闲置连接：可以调短（如 30–60 秒），平衡资源占用。

总之，keepalive_timeout=300 就是告诉 aiohttp：空闲连接，先别急着扔；多等 5 分钟，如果还没用就回收，保证性能和资源利用率的双赢。

### 下一次建立长连接的时候？？

`keepalive_timeout` 是在 Connector 级别统一生效的 —— 不管是应用启动时建立的第一批连接，还是空闲过后被回收再新建的后续连接，它们都遵循同一个 `keepalive_timeout` 值。

文档说明：

“keepalive_timeout (float) – timeout for connection reusing after releasing (optional). Values 0. For disabling keep-alive feature use force_close=True flag.”


基类 BaseConnector 定义了这个参数，所有从它派生的 TCPConnector 都继承此行为 https://docs.aiohttp.org/en/stable/client_reference.html

#### 源码解读

在 aiohttp.connector.BaseConnector 中，对空闲连接的清理逻辑如下（节选自 3.12.13 版源码）：

```python
def _cleanup(self) -> None:
    now = monotonic()
    timeout = self._keepalive_timeout
    if self._conns:
        ...
        for key, conns in self._conns.items():
            for proto, use_time in conns:
                # 如果连接最后使用时间超过 timeout，关闭它
                if now - use_time >= timeout:
                    proto.transport.close()
        ...
```

`self._keepalive_timeout` 就是构造时传入的 keepalive_timeout（你的 300 秒）。

每当连接释放回池中（即 Connection.release()），它会被压入 `_conns` 队列，并在下一次 `_cleanup` 调用时被检查空闲时长。

无论连接是首次建立还是后续重建（例如遇到 DNS 变更、SSL 握手失败等触发重新连接），它们都会复用同一个 TCPConnector 实例，继承同样的 keepalive_timeout 设置。

##### 补充说明

- 主动关闭：若将 `force_close=True` ，则关闭池中所有连接、每次请求后也都会强制新建连接，此时 `keepalive_timeout` 不生效。

- SSL 清理：对于 SSL 连接，_cleanup 之后还会有额外的 `_cleanup_closed` 逻辑来确保底层传输彻底关闭。