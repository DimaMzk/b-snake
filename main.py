from graph_algorithms import find_path, generate_waypoints, link_waypoints, enough_space
import bottle
import os
import time

EMPTY = 0
WALL = 1
SNAKE = 2
FOOD = 3
DANGER = 4
SNAKE_HEAD = 5
SNAKE_TAIL = 6
DEAD_END = 7
DIRECTIONS = ['up', 'down', 'left', 'right']
BAD_POSITIONS = [WALL, SNAKE, DANGER, SNAKE_HEAD, SNAKE_TAIL, DEAD_END]
PATH_FINDING_OBSTACLES = [WALL, SNAKE, DANGER, SNAKE_HEAD, SNAKE_TAIL]
GOOD_POSITIONS = [EMPTY, FOOD]
DEATH_POSITIONS = [WALL, SNAKE, SNAKE_HEAD]
taunt = 'Make money sell money'


def point_to_list(json_object):
    return (json_object['x'], json_object['y'])


def objectives(data):
    results = []
    food = data['food']['data']
    for f in food:
        results.append(point_to_list(f))
    return results


def display_grid(grid):
    print('Displaying game state:')
    for y in range(len(grid)):
        row = ""
        for x in range(len(grid[y])):
            row = row + str(grid[x][y]) + " "
        print(row)


def generate_grid(snake_id, my_snake_length, data):
    grid = [[0 for col in range(data['height'])] for row in range(data['width'])]

    for food in data['food']['data']:
        food = point_to_list(food)
        grid[food[0]][food[1]] = FOOD

    for snake in data['snakes']['data']:
        for coord in snake['body']['data']:
            coord = point_to_list(coord)
            # Add in once accounting for eating an apple
            # if coord != snake['coords'][-1]:
            grid[coord[0]][coord[1]] = SNAKE

        if snake_id != snake['id']:
            if my_snake_length <= snake['length']:
                danger_spots = neighbours(point_to_list(snake['body']['data'][0]), grid, BAD_POSITIONS)
                for n in danger_spots:
                    grid[n[0]][n[1]] = DANGER
        snake_head = point_to_list(snake['body']['data'][-1])
        grid[snake_head[0]][snake_head[1]] = SNAKE_TAIL
        snake_head = point_to_list(snake['body']['data'][0])
        grid[snake_head[0]][snake_head[1]] = SNAKE_HEAD

    # start = time.time()
    possible_dead_end = []
    for y in range(len(grid)):
        for x in range(len(grid[y])):
            pos = (x, y)
            if grid[x][y] in GOOD_POSITIONS:
                neigh = neighbours(pos, grid, BAD_POSITIONS)
                if(len(neigh) <= 1):
                    grid[x][y] = DEAD_END
                    for n in neigh:
                        possible_dead_end.append(n)
                    # print('Found dead end')
    while len(possible_dead_end) > 0:
        for pos in possible_dead_end:
            possible_dead_end.remove(pos)
            if grid[pos[0]][pos[1]] in GOOD_POSITIONS:
                neigh = neighbours(pos, grid, BAD_POSITIONS)
                if(len(neigh) <= 1):
                    grid[pos[0]][pos[1]] = DEAD_END
                    for n in neigh:
                        possible_dead_end.append(n)
                    # print('Found dead end')
    # end = time.time()
    # print('Time to tag DEAD_ENDs: ' + str((end - start) * 1000) + 'ms')
    # display_grid(grid)
    return grid


def direction(a, b):
    if(a[0] > b[0]):
        return 'left'
    if(a[0] < b[0]):
        return 'right'
    if(a[1] > b[1]):
        return 'up'
    if(a[1] < b[1]):
        return 'down'


def smart_direction(a, b, grid, obstacles, overlapping):
    raw_move = direction(a, b)
    if(move_to_position(a, raw_move)[0] == b[0] and move_to_position(a, raw_move)[1] == b[1] and not overlapping):
        return raw_move
    if(a[0] > b[0] and grid[a[0] - 1][a[1]] not in obstacles):
        return 'left'
    if(a[0] < b[0] and grid[a[0] + 1][a[1]] not in obstacles):
        return 'right'
    if(a[1] > b[1] and grid[a[0]][a[1] - 1] not in obstacles):
        return 'up'
    if(a[1] < b[1] and grid[a[0]][a[1] + 1] not in obstacles):
        return 'down'


def move_to_position(origin, direction):
    if direction is 'up':
        return (origin[0], origin[1] - 1)
    if direction is 'down':
        return (origin[0], origin[1] + 1)
    if direction is 'right':
        return (origin[0] + 1, origin[1])
    if direction is 'left':
        return (origin[0] - 1, origin[1])


def path_distance(path):
    dis = 0
    path = tuple(path)
    index = 0
    while index < len(path) - 1:
        dis = dis + distance(path[index], path[index + 1])
        index = index + 1
    return dis


def distance(a, b):
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return dx+dy


def neighbours(node, grid, ignore_list):
    width = len(grid)
    height = len(grid[0])
    result = []
    if(node[0] > 0):
        result.append((node[0]-1, node[1]))
    if(node[0] < width - 1):
        result.append((node[0]+1, node[1]))
    if(node[1] > 0):
        result.append((node[0], node[1]-1))
    if(node[1] < height-1):
        result.append((node[0], node[1]+1))
    result = filter(lambda n: (grid[n[0]][n[1]] not in ignore_list), result)
    open_set = []
    for r in result:
        open_set.append(r)
    return open_set


def is_body_overlapping(body):
    for b in body:
        counter = 0
        for d in body:
            if b == d:
                counter = counter + 1
        if counter > 1:
            return True
    return False


def enemy_near_tail(my_head, my_tail, grid):
    for n in neighbours(my_tail, grid, []):
        if n[0] == my_head[0] and n[1] == my_head[1]:
            continue
        if grid[n[0]][n[1]] == SNAKE_HEAD:
            return True
            print('Enemy near tail')
    return False


def get_snake_tails(data):
    tails = []
    for snake in data['snakes']['data']:
        snake_tail = point_to_list(snake['body']['data'][-1])
        tails.append(snake_tail)
    return tails


def run_ai(data):
    # Important Info:
    global taunt
    move = 'default'
    snake_id = data['you']['id']
    goals = objectives(data)
    my_snake_length = data['you']['length']
    my_snake_health = data['you']['health']
    # TODO Update for all body not just starting body
    my_snake_overlapping = is_body_overlapping(data['you']['body']['data'])

    if my_snake_health < 15:
        print('About to die of hunger!')
    grid = generate_grid(snake_id, my_snake_length, data)
    # display_grid(grid)
    my_snake_head = point_to_list(data['you']['body']['data'][0])
    my_snake_tail = point_to_list(data['you']['body']['data'][-1])
    snakes = data['snakes']['data']
    # Do I want or need food?
    # Can I bully?
    # Should I find free space?
    # Is food near me?
    # Safe Roam or chase tail?

    start = time.time()
    interest_points = []
    interest_points.append(my_snake_head)
    for tail in get_snake_tails(data):
        interest_points.append(tail)
    waypoints = generate_waypoints(grid, PATH_FINDING_OBSTACLES, interest_points)
    end = time.time()
    print('Time to waypoints: ' + str((end - start) * 1000) + 'ms')
    start = time.time()
    links = link_waypoints(waypoints, grid, PATH_FINDING_OBSTACLES)
    end = time.time()
    print('Time to link waypoints: ' + str((end - start) * 1000) + 'ms')
    # display_grid(grid)
    current_path = None

    if my_snake_health < 50 or my_snake_length < 12:
        current_path = path_to_safe_food(my_snake_head, my_snake_length, snake_id, goals, snakes, waypoints, links, grid, my_snake_overlapping)
    elif my_snake_health < 20:
        current_path = path_to_desperation_food(my_snake_head, my_snake_length, snake_id, goals, waypoints, links, grid, my_snake_overlapping)
    if current_path is not None:
        '''print('Printing path')
        for n in current_path:
            print(n)'''
        move = smart_direction(my_snake_head, current_path[1], grid, PATH_FINDING_OBSTACLES, my_snake_overlapping)
        print('Going to food at ' + str(current_path[1]) + ' by going ' + str(move))
    else:
        # bully smaller enemy
        current_path = path_to_bully_enemy(my_snake_head, my_snake_length, snake_id, goals, snakes, waypoints, links, grid, my_snake_overlapping)
        can_bully_enemy = True
        if current_path is not None:
            if len(current_path) > 1:
                # print('overlapping:' + str(my_snake_overlapping))
                possible_move = smart_direction(my_snake_head, current_path[1], grid, PATH_FINDING_OBSTACLES, my_snake_overlapping)
                # display_grid(grid)
                # print(current_path)
                if possible_move is not None:
                    move = possible_move
                    print('Going to bully enemy at' + str(current_path[-1]) + ' by going ' + str(move))
                else:
                    print('Could not find move to bully enemy')
                    can_bully_enemy = False
            else:
                can_bully_enemy = False
        else:
            can_bully_enemy = False
        if not can_bully_enemy:
            # follow tail
            if not enemy_near_tail(my_snake_head, my_snake_tail, grid):
                current_path = path_to_tail(my_snake_head, my_snake_tail, waypoints, links, grid)
            if current_path is not None:
                if len(current_path) > 1:
                    # print('overlapping:' + str(my_snake_overlapping))
                    possible_move = smart_direction(my_snake_head, current_path[1], grid, PATH_FINDING_OBSTACLES, my_snake_overlapping)
                    # display_grid(grid)
                    # print(current_path)
                    if possible_move is not None:
                        move = possible_move
                        print('Going to tail at' + str(current_path[1]) + ' by going ' + str(move))
                    else:
                        print('Could not find move to tail')
                        move = find_best_move(my_snake_head, my_snake_tail, snake_id, snakes, grid, waypoints, links, my_snake_overlapping)
            else:
                print('Desperation Move time...')
                move = find_best_move(my_snake_head, my_snake_tail, snake_id, snakes, grid, waypoints, links, my_snake_overlapping)

    print('Moving ' + str(move))
    return move


def path_to_safe_food(my_snake_head, my_snake_length, snake_id, goals, snakes, waypoints, links, grid, my_snake_overlapping):
    current_path = None
    for goal in goals:
        if current_path is not None:
            if distance(my_snake_head, goal) > path_distance(current_path):
                continue
        easy = True
        for snake in snakes:
            if(snake['id'] != snake_id):
                enemy_dist = distance(point_to_list(snake['body']['data'][0]), goal)
                if enemy_dist <= distance(my_snake_head, goal):
                    easy = False
                    break
        if not easy:
            continue
        # start = time.time()
        path = find_path(my_snake_head, goal, waypoints, links, grid, PATH_FINDING_OBSTACLES)
        # end = time.time()
        # print('Time to get path from o_path: ' + str((end - start) * 1000) + 'ms')
        if path is not None:
            possible_move = smart_direction(my_snake_head, path[1], grid, [], my_snake_overlapping)
            # print('possible_move:' + str(possible_move))
            # print(path)
            block_pos = move_to_position(my_snake_head, possible_move)
            # display_grid(grid)
            # print('block pos:' + str(block_pos))
            temp_hold = grid[block_pos[0]][block_pos[1]]
            grid[block_pos[0]][block_pos[1]] = SNAKE_HEAD
            if my_snake_length <= enough_space(path[-1], my_snake_length, grid, BAD_POSITIONS):
                if current_path is not None:
                    if(path_distance(path) < path_distance(current_path)):
                        current_path = path
                else:
                    current_path = path
            grid[block_pos[0]][block_pos[1]] = temp_hold
            # display_grid(grid)
            # end = time.time()
            # print('Time to fill: ' + str((end - start) * 1000) + 'ms')
    return current_path


def path_to_desperation_food(my_snake_head, my_snake_length, snake_id, goals, waypoints, links, grid, my_snake_overlapping):
    display_grid(grid)
    current_path = None
    for goal in goals:
        if current_path is not None:
            if distance(my_snake_head, goal) > path_distance(current_path):
                continue
        # start = time.time()
        path = find_path(my_snake_head, goal, waypoints, links, grid, BAD_POSITIONS)
        # end = time.time()
        # print('Time to get path from o_path: ' + str((end - start) * 1000) + 'ms')
        if path is not None:
            possible_move = smart_direction(my_snake_head, path[1], grid, PATH_FINDING_OBSTACLES, my_snake_overlapping)
            block_pos = move_to_position(my_snake_head, possible_move)
            temp_hold = grid[block_pos[0]][block_pos[1]]
            grid[block_pos[0]][block_pos[1]] = SNAKE_HEAD
            if my_snake_length <= enough_space(goal, my_snake_length, grid, BAD_POSITIONS):
                if current_path is not None:
                    if(path_distance(path) < path_distance(current_path)):
                        current_path = path
                else:
                    current_path = path

            grid[block_pos[0]][block_pos[1]] = temp_hold
        # end = time.time()
        # print('Time to fill: ' + str((end - start) * 1000) + 'ms')
    return current_path


def path_to_convenient_food():
    return


def path_to_tail(my_snake_head, my_snake_tail, waypoints, links, grid):
    global taunt
    current_path = None
    tail_neighbours = neighbours(my_snake_tail, grid, [])
    for n in tail_neighbours:
        path = None
        # print('Looking for tail at ' + str(n) + ' my head at ' + str(my_snake_head))
        if n[0] == my_snake_head[0] and n[1] == my_snake_head[1]:
            r = []
            r.append(my_snake_tail)
            r.append(my_snake_tail)
            current_path = r
            taunt = 'Just going to eat my tail...'
            break
        if n in PATH_FINDING_OBSTACLES:
            continue
        path = find_path(my_snake_head, n, waypoints, links, grid, PATH_FINDING_OBSTACLES)
        if path is not None:
            # print(str(path))
            if current_path is not None:
                if path_distance(current_path) > path_distance(path):
                    current_path = path
            else:
                current_path = path
    if current_path is not None:
        print('Found path to tail')
    else:
        print('Could not find path to tail')
    return current_path


def path_to_enemy_tail(my_snake_head, snake_id, snakes, waypoints, links, grid):
    global taunt
    current_path = None
    for snake in snakes:
        if snake_id == snake['id']:
            continue
        enemy_tail = point_to_list(snake['body']['data'][-1])
        tail_neighbours = neighbours(enemy_tail, grid, [])
        for n in tail_neighbours:
            path = None
            # print('Looking for tail at ' + str(n) + ' my head at ' + str(my_snake_head))
            if n in PATH_FINDING_OBSTACLES:
                continue
            path = find_path(my_snake_head, n, waypoints, links, grid, PATH_FINDING_OBSTACLES)
            if path is not None:
                # print(str(path))
                if current_path is not None:
                    if path_distance(current_path) > path_distance(path):
                        current_path = path
                else:
                    current_path = path
    if current_path is not None:
        taunt = 'Nice tail, where ya from?'
        print('Found path to enemy tail')
    return current_path


def path_to_bully_enemy(my_snake_head, my_snake_length, snake_id, goals, snakes, waypoints, links, grid, my_snake_overlapping):
    # TODO make sure target does not have the opportunity to block my snake. Could happen when against walls
    global taunt
    current_path = None
    for snake in snakes:
        if snake_id == snake['id']:
            continue
        if my_snake_length <= snake['length']:
            continue
        enemy_head = point_to_list(snake['body']['data'][0])
        head_neighbours = neighbours(enemy_head, grid, [])
        for n in head_neighbours:
            path = None
            # print('Looking for tail at ' + str(n) + ' my head at ' + str(my_snake_head))
            if n in BAD_POSITIONS:
                continue
            path = find_path(my_snake_head, n, waypoints, links, grid, PATH_FINDING_OBSTACLES)

            if path is not None:
                if len(path) < 2:
                    continue
                # Check if another enemy is closer
                easy = True
                for s in snakes:
                    if(not s['id'] == snake_id and not s['id'] == snake['id']):
                        enemy_dist = distance(point_to_list(s['body']['data'][0]), n)
                        if enemy_dist <= path_distance(path):
                            easy = False
                            break
                if not easy:
                    # print('another enemy closer')
                    continue
                # Check if move would lead to snake getting trapped
                possible_move = smart_direction(my_snake_head, path[1], grid, PATH_FINDING_OBSTACLES, my_snake_overlapping)
                block_pos = move_to_position(my_snake_head, possible_move)
                # print('possible moves after attack: ' + str(neighbours(block_pos, grid, PATH_FINDING_OBSTACLES)))
                if len(neighbours(block_pos, grid, PATH_FINDING_OBSTACLES)) == 0:
                    continue
                temp_hold = grid[block_pos[0]][block_pos[1]]
                grid[block_pos[0]][block_pos[1]] = SNAKE_HEAD
                if len(neighbours(block_pos, grid, PATH_FINDING_OBSTACLES)) <= 2:
                    grid[block_pos[0]][block_pos[1]] = temp_hold
                    continue
                if len(neighbours(path[-1], grid, PATH_FINDING_OBSTACLES)) == 0:
                    taunt = 'Say goodbye!'
                    print('Moving in the kill enemy')
                    grid[block_pos[0]][block_pos[1]] = temp_hold
                    return path
                target_surrounding_node = neighbours(block_pos, grid, PATH_FINDING_OBSTACLES)[0]
                if my_snake_length <= enough_space(target_surrounding_node, my_snake_length, grid, BAD_POSITIONS):

                    if current_path is not None:
                        if(path_distance(path) < path_distance(current_path)):
                            current_path = path
                    else:
                        current_path = path
                grid[block_pos[0]][block_pos[1]] = temp_hold
    if current_path is not None:
        taunt = 'I\'m coming for you!'
        # print('Found path to bully enemy')
    return current_path


def find_best_move(my_snake_head, my_snake_tail, snake_id, snakes, grid, waypoints, links, my_snake_overlapping):
    global taunt
    # TODO: FIND LARGEST PATH OR MOVE TO CENTRE
    possible_positions = neighbours(my_snake_head, grid, [1])
    found_tail = False
    if len(possible_positions) > 0:
        # print('Trying to the best of the worst moves... looking for my tail...')
        for p in possible_positions:
            if p[0] == my_snake_tail[0] and p[1] == my_snake_tail[1] and not my_snake_overlapping and not enemy_near_tail(my_snake_head, my_snake_tail, grid):
                move = direction(my_snake_head, my_snake_tail)
                found_tail = True
                taunt = 'Look at dat tail!'
                print('Found my tail!')
                break
    if not found_tail:
        found_enemy_tail = False
        path = path_to_enemy_tail(my_snake_head, snake_id, snakes, waypoints, links, grid)
        if path is not None:
            if len(path) > 1:
                found_enemy_tail = True
                print(path)
                move = smart_direction(my_snake_head, path[1], grid, PATH_FINDING_OBSTACLES, my_snake_overlapping)
                print('Following enemy tail in desperation')
        if not found_enemy_tail:
            possible_positions = neighbours(my_snake_head, grid, BAD_POSITIONS)
            if len(possible_positions) > 0:
                taunt = 'I love the smell of battle snake in the...'
                print('Found an empty spot!')
                move = direction(my_snake_head, possible_positions[0])
            else:
                possible_positions = neighbours(my_snake_head, grid, DEATH_POSITIONS)
                if len(possible_positions) > 0:
                    taunt = 'I taste bad! Don\'t eat me!'
                    move = direction(my_snake_head, possible_positions[0])
                    print('Desperation move!')
                else:
                    move = 'down'
                    taunt = 'That was irrational of you. Not to mention unsportsmanlike.'
                    print('No where to go!!!')
    # print('No decient moves so moving ' + move)
    return move


@bottle.post('/start')
def start():
    data = bottle.request.json
    if data is not None:
        game_id = data['game_id']
        print("New game started!")
        board_width = data['width']
        board_height = data['height']
        print(str(game_id) + " " + str(board_width) + " " + str(board_height))

    # TODO: Do things with data

    return {
        'color': 'DarkMagenta',
        'secondary_color': 'red',
        'taunt': 'Time for some b snake boys!',
        'name': 'Lil Big B',
        'head_url': 'http://i.dailymail.co.uk/i/pix/2011/05/20/article-1389216-0C2E35E200000578-582_634x611.jpg'
    }


@bottle.post('/move')
def move():
    global taunt
    data = bottle.request.json
    # print(str(data))
    taunt = 'Lil B Big Snake'
    start = time.time()
    output = run_ai(data)
    end = time.time()
    print('Time to get AI move: ' + str((end - start) * 1000) + 'ms')
    return {
        'move': output,
        'taunt': taunt
    }


@bottle.get('/')
def status():
    return{
        "<!DOCKTYPE html><html><head><title>2018</title><style>p{color:orange;}</style></head><body><p>BattleSnake 2018 by Mitchell Nursey.</p></body></html>"
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()
if __name__ == '__main__':
    bottle.run(application, server='auto', host=os.getenv('IP', '0.0.0.0'), port=os.getenv('PORT', '8080'))
