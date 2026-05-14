def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        # 末尾i个元素已经有序，无需重复比较
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        # 本轮无交换说明数组已经完全有序，提前退出
        if not swapped:
            break
    return arr


if __name__ == "__main__":
    test_array = [64, 34, 25, 12, 22, 11, 90]
    sorted_array = bubble_sort(test_array)
    print("排序结果：", sorted_array)
