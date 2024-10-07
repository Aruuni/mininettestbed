run() {
    UBUNTU_VERSION=$(lsb_release -r | awk '{print $2}')

    if [[ "$UBUNTU_VERSION" == "16.04" ]]; then
        time python3.7 "$@"
    else
        time python3 "$@"
    fi
}