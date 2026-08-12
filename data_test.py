from scanner import get_klines


df = get_klines(
    symbol="BTC-SWAP-USDT",
    interval="1h",
    limit=100
)

print("\nROWS:", len(df))

print("\nFIRST 5:")
print(
    df[
        [
            "open_time",
            "open",
            "high",
            "low",
            "close"
        ]
    ].head(5)
)

print("\nLAST 5:")
print(
    df[
        [
            "open_time",
            "open",
            "high",
            "low",
            "close"
        ]
    ].tail(5)
)

print("\nTIME ORDER:")

print(
    df["open_time"].is_monotonic_increasing
)

print("\nDUPLICATES:")

print(
    df["open_time"].duplicated().sum()
)

print("\nCLOSE FIRST:")

print(
    df["close"].iloc[0]
)

print("\nCLOSE LAST:")

print(
    df["close"].iloc[-1]
)
