#!/usr/bin/python
#
# From:
#
#      5
#     / \
#   2     4
#  / \     \
# 8   3     5
#
# To:
#
# 5
# 2 4
# 8 3 5

class Node(object):
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right

def print_tree(root):
    elements = []
    out = []

    elements.append(root)
    item, nextitem = 1, 0

    while item:
        n = elements.pop(0)

        if n:
            out.append(str(n.value))
            item -= 1

            # n.right: Node class with right attr not None
            # n.left: Node class with left attr not None
            for p in (n.right, n.left):
                if p:
                    elements.append(p)
                    nextitem += 1

        # 0 has value of False
        if not item:
            out.reverse()
            print ' '.join(out)
            out = []
            item, nextitem = nextitem, 0

root = Node(5, Node(2, Node(8), Node(3)), Node(4, None, Node(5)))
print_tree(root)
