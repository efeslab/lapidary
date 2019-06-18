//gistsnip:start:runlapidary
python3 -m lapidary create --cmd ./test/bin/test --interval 1 -c ./test/lapidary.yaml
python3 -m lapidary parallel-simulate --directory ./test_checkpoints -c ./test/lapidary.yaml
//gistsnip:end:runlapidary
