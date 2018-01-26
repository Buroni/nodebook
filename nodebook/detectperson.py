class detectperson:
    def neighborhood_overlap(self, v1, v2, G):
        if (v1,v2) not in G.edges() and (v2,v1) not in G.edges():
            return -1
        try:
            G.neighbors(v1)
            G.neighbors(v2)
        except:
            return 0.0
        v1_neighbors = G.neighbors(v1)
        v2_neighbors = G.neighbors(v2)
        total_num_neighbors = len(list(set().union(v1_neighbors, v2_neighbors))) - 2
        total_num_shared = len(list(set(v1_neighbors) & set(v2_neighbors)))
        try:
            float(total_num_shared) / total_num_neighbors
        except ZeroDivisionError:
            return 0.0
        else:
            # return total_num_neighbors
            return float(total_num_shared) / total_num_neighbors

    def all_overlaps(self, G):
        overlaps = {}
        for char2 in G:
            if overlaps.get((char2, "[FP]"), -1) != -1 or "[FP]" == char2:
                continue
            overlap = self.neighborhood_overlap("[FP]", char2, G)
            if overlap != -1:
                overlaps[("[FP]", char2)] = overlap
        return overlaps

    def is_1stperson(self, lines):
        fp_count = 0
        for i,line in enumerate(lines):
            if "[FP]" in line:
                fp_count += 1
            if fp_count > 50:
                return True
            if i == 500:
                return False
